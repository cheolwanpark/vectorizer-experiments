#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import benchmark_sources
except ModuleNotFoundError:
    from scripts import benchmark_sources


DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_LOG_ROOT = "artifacts/emulate"
DEFAULT_SIMUL = "gem5"
DEFAULT_GEM5_TARGET = "xiangshan"
CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_BUILD_OUTPUT_ROOT = CONTAINER_OUTPUT_ROOT / "build"
CONTAINER_EMULATOR_ROOT = Path("/workspace/emulator")
CONTAINER_TSVC_SRC_ROOT = CONTAINER_EMULATOR_ROOT / "benchmarks" / "TSVC_2" / "src"
RUN_SIM_PATH = Path("/workspace/emulator/run-sim.sh")
SIM_TARGET = "xiangshan.KunminghuV2Config"
DEFAULT_RTL_TARGET = SIM_TARGET
LEGACY_TIMEOUT_S = 120
XIANSHAN_DEFAULT_TIMEOUT_S = 1800
BUILD_ARTIFACT_SUFFIXES = {
    "opt_ll_text": ".opt.ll",
    "asm_text": ".s",
}
SUPPORTED_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".s", ".S"}
MANIFEST_FILENAME = "manifest.yaml"
VALID_SIMULATORS = frozenset({"gem5", "rtl"})
VALID_GEM5_TARGETS = frozenset({"gem5", "xiangshan"})


@dataclass(frozen=True)
class SimulatorConfig:
    simul: str
    simulator_target: str
    gem5_target: str
    rtl_target: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one workload through the selected emulator backend in Docker and write a host-side report."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--bench", help="Benchmark name, for example s000")
    source_group.add_argument(
        "--source",
        help="Repo-local workload input path to build and emulate (.c, .s, .S, or manifest.yaml)",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--len", type=int, default=4096, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value")
    parser.add_argument(
        "--use-vf",
        default="",
        help="Force loop vectorization with LLVM -vplan-use-vf syntax, for example fixed:4 or scalable:2",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Simulation timeout in seconds")
    parser.add_argument(
        "--log-root",
        default=DEFAULT_LOG_ROOT,
        help="Host output root for reports and raw artifacts",
    )
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang via --cflags")
    parser.add_argument("--extra-opt-flags", default="", help="Extra flags passed to opt via --optflags")
    parser.add_argument(
        "--simul",
        choices=sorted(VALID_SIMULATORS),
        default=None,
        help=f"Execution backend (env: SIMUL, default: {DEFAULT_SIMUL})",
    )
    parser.add_argument(
        "--gem5-target",
        default=None,
        help=f"gem5 build profile token (env: GEM5_TARGET, default: {DEFAULT_GEM5_TARGET})",
    )
    parser.add_argument(
        "--rtl-target",
        default=None,
        help=f"RTL simulator target (env: RTL_TARGET, default: {DEFAULT_RTL_TARGET})",
    )
    return parser.parse_args()


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def validate_positive_int(name: str, value: int | None) -> None:
    if value is not None and value <= 0:
        fail(f"{name} must be a positive integer")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_image_exists(image: str) -> None:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        fail(
            f"Docker image not found: {image}\n"
            f"Build or tag the image first, for example: docker build -t {DEFAULT_IMAGE} ."
        )


def timestamp_dir(root: Path, bench: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    out_dir = root / bench / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir


def parse_int(text: str) -> int:
    return int(text.replace(",", ""))


def parse_float(text: str) -> float:
    return float(text.strip())


def validate_vplan_use_vf(text: str) -> None:
    if not text:
        return
    for entry in text.split(","):
        if entry == "-":
            continue
        match = re.fullmatch(r"(fixed|scalable):([0-9]+)", entry)
        if not match:
            fail(
                "use-vf must match LLVM -vplan-use-vf syntax, "
                "for example fixed:4,-,scalable:2"
            )
        width = int(match.group(2))
        if width <= 0 or width & (width - 1):
            fail("use-vf widths must be positive powers of two")


def resolve_simulator_config(
    *,
    simul: str | None = None,
    gem5_target: str | None = None,
    rtl_target: str | None = None,
) -> SimulatorConfig:
    resolved_simul = (simul or os.environ.get("SIMUL", DEFAULT_SIMUL)).strip().lower()
    if resolved_simul not in VALID_SIMULATORS:
        allowed = ", ".join(sorted(VALID_SIMULATORS))
        fail(f"SIMUL must be one of: {allowed}")

    resolved_gem5_target = (gem5_target or os.environ.get("GEM5_TARGET", DEFAULT_GEM5_TARGET)).strip().lower()
    if resolved_gem5_target not in VALID_GEM5_TARGETS:
        allowed = ", ".join(sorted(VALID_GEM5_TARGETS))
        fail(f"GEM5_TARGET must be one of: {allowed}")

    resolved_rtl_target = (rtl_target or os.environ.get("RTL_TARGET", DEFAULT_RTL_TARGET)).strip()
    if not resolved_rtl_target:
        fail("RTL_TARGET must not be empty")

    simulator_target = "gem5" if resolved_simul == "gem5" else resolved_rtl_target
    return SimulatorConfig(
        simul=resolved_simul,
        simulator_target=simulator_target,
        gem5_target=resolved_gem5_target,
        rtl_target=resolved_rtl_target,
    )


def resolve_timeout(timeout_s: int, sim_config: SimulatorConfig) -> int:
    if timeout_s == LEGACY_TIMEOUT_S and sim_config.simul == "rtl" and sim_config.rtl_target == DEFAULT_RTL_TARGET:
        return XIANSHAN_DEFAULT_TIMEOUT_S
    return timeout_s


def parse_run_sim_output(text: str) -> dict[str, object]:
    patterns: dict[str, tuple[str, callable]] = {
        "status": (r"^Status:\s+(.+)$", str),
        "exit_code": (r"^Exit code:\s+(-?\d+)$", int),
        "wall_time_s": (r"^Wall time:\s+([0-9.]+)s$", parse_float),
        "kernel_cycles": (r"^Kernel:\s+([\d,]+)\s+cycles$", parse_int),
        "total_cycles": (r"^Total sim:\s+([\d,]+)\s+cycles$", parse_int),
        "sim_speed_khz": (r"^Sim speed:\s+([0-9.]+)\s+kHz$", parse_float),
        "run_detail_path": (r"^Log file:\s+(.+)$", str),
        "trace_file": (r"^Trace:\s+(.+)$", str),
        "built_workload": (r"^Built:\s+(.+)$", str),
        "asm_outputs": (r"^Asm outputs:\s+(.+)$", json.loads),
        "ir_outputs": (r"^IR outputs:\s+(.+)$", json.loads),
    }
    summary: dict[str, object] = {}
    for key, (pattern, caster) in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            summary[key] = caster(match.group(1).strip())
    return summary


def map_container_output_path(path_text: str, host_output_dir: Path) -> Path:
    path = Path(path_text)
    try:
        relative = path.relative_to(CONTAINER_OUTPUT_ROOT)
    except ValueError:
        return path
    return host_output_dir / relative


def load_build_artifact_texts(
    host_output_dir: Path,
    built_workload: str | None,
    *,
    asm_outputs: list[str] | None = None,
    ir_outputs: list[str] | None = None,
) -> dict[str, str]:
    texts = {name: "" for name in BUILD_ARTIFACT_SUFFIXES}

    if ir_outputs:
        host_ir = map_container_output_path(ir_outputs[0], host_output_dir)
        if host_ir.exists():
            texts["opt_ll_text"] = host_ir.read_text(encoding="utf-8")
    if asm_outputs:
        host_asm = map_container_output_path(asm_outputs[0], host_output_dir)
        if host_asm.exists():
            texts["asm_text"] = host_asm.read_text(encoding="utf-8")
    if any(texts.values()) or not built_workload:
        return texts

    if not built_workload:
        return {name: "" for name in BUILD_ARTIFACT_SUFFIXES}

    host_workload = map_container_output_path(built_workload, host_output_dir)
    base_path = host_workload.with_suffix("") if host_workload.suffix else host_workload
    for field_name, suffix in BUILD_ARTIFACT_SUFFIXES.items():
        artifact_path = base_path.parent / f"{base_path.name}{suffix}"
        texts[field_name] = (
            artifact_path.read_text(encoding="utf-8") if artifact_path.exists() else ""
        )
    return texts


def build_markdown_report(summary: dict[str, object]) -> str:
    forced_vf = summary.get("use_vf") or "default"
    trace_file = summary.get("trace_file", "n/a")
    backend = str(summary.get("simul", "unknown"))
    gem5_profile = summary.get("gem5_target", "n/a") if backend == "gem5" else "n/a"
    rtl_target = summary.get("rtl_target", "n/a") if backend == "rtl" else "n/a"
    lines = [
        f"# Emulate Report: `{summary['benchmark']}`",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Backend | `{backend}` |",
        f"| Simulator target | `{summary['simulator_target']}` |",
        f"| gem5 profile | `{gem5_profile}` |",
        f"| RTL target | `{rtl_target}` |",
        f"| Status | `{summary.get('status', 'unknown')}` |",
        f"| Exit code | `{summary.get('exit_code', 'n/a')}` |",
        f"| LEN | `{summary['len_1d']}` |",
        f"| LMUL | `{summary['lmul']}` |",
        f"| Forced VF | `{forced_vf}` |",
        f"| Kernel cycles | `{summary.get('kernel_cycles', 'n/a')}` |",
        f"| Total cycles | `{summary.get('total_cycles', 'n/a')}` |",
        f"| Wall time (s) | `{summary.get('wall_time_s', 'n/a')}` |",
        f"| Sim speed (kHz) | `{summary.get('sim_speed_khz', 'n/a')}` |",
        "",
        "## Paths",
        "",
        f"- Artifacts: `{summary['artifact_dir']}`",
        f"- Container log: `{summary['container_log']}`",
        f"- Run detail: `{summary.get('run_detail_path', 'n/a')}`",
        f"- Trace: `{trace_file}`",
        "",
        "## Command",
        "",
        "```bash",
        summary["docker_command"],
        "```",
        "",
    ]
    return "\n".join(lines)


def print_summary(summary: dict[str, object]) -> None:
    forced_vf = summary.get("use_vf") or "default"
    timeout_s = summary.get("effective_timeout_s", summary.get("timeout_s", "n/a"))
    backend = str(summary.get("simul", "unknown"))
    profile_value = summary.get("gem5_target", "n/a") if backend == "gem5" else summary.get("rtl_target", "n/a")
    lines = [
        f"Benchmark:  {summary['benchmark']}",
        f"Backend:    {backend}",
        f"Target:     {summary['simulator_target']}",
        f"Profile:    {profile_value}",
        f"Status:     {summary.get('status', 'unknown')}",
        f"Forced VF:  {forced_vf}",
        f"Timeout:    {timeout_s}s",
        f"Kernel:     {summary.get('kernel_cycles', 'n/a')} cycles",
        f"Total sim:  {summary.get('total_cycles', 'n/a')} cycles",
        f"Wall time:  {summary.get('wall_time_s', 'n/a')}s",
        f"Sim speed:  {summary.get('sim_speed_khz', 'n/a')} kHz",
        f"Artifacts:  {summary['artifact_dir']}",
    ]
    print("\n".join(lines))


def resolve_log_root(root: Path, log_root: str) -> Path:
    path = Path(log_root)
    if not path.is_absolute():
        path = (root / path).resolve()
    return path


def resolve_tsvc_src_root(root: Path) -> Path:
    return root / "emulator" / "benchmarks" / "TSVC_2" / "src"


def resolve_benchmark_input(root: Path, bench: str) -> Path:
    return benchmark_sources.resolve_workload_input(root, bench)


def resolve_source_path(root: Path, source: str | Path) -> Path:
    root = root.resolve()
    path = Path(source)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"benchmark source not found: {path}")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"benchmark source must be inside repo root: {path}") from exc
    return path


def validate_source_suffix(source: Path) -> None:
    if source.name == MANIFEST_FILENAME:
        return
    if source.suffix not in SUPPORTED_SOURCE_SUFFIXES:
        fail(f"source must be a .c, .s, .S, or manifest.yaml file: {source}")


def benchmark_name_for_input(source: Path) -> str:
    if source.name == MANIFEST_FILENAME:
        data = benchmark_sources.load_mapping_file(source)
        return str(data.get("name") or source.parent.name)
    return source.stem


def build_emulate_docker_command(
    *,
    root: Path,
    out_dir: Path,
    source: Path,
    sim_config: SimulatorConfig,
    image: str,
    len_1d: int,
    lmul: int,
    use_vf: str,
    effective_timeout: int,
    extra_cflags: str = "",
    extra_opt_flags: str = "",
) -> list[str]:
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        DEFAULT_PLATFORM,
        "-v",
        f"{root}:{CONTAINER_PROJECT_ROOT}:ro",
        "-v",
        f"{out_dir}:{CONTAINER_OUTPUT_ROOT}",
        "-v",
        f"{root / 'emulator' / 'run-sim.sh'}:{RUN_SIM_PATH}:ro",
        "-v",
        f"{root / 'emulator' / 'sim-configs.yaml'}:{CONTAINER_EMULATOR_ROOT / 'sim-configs.yaml'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'build-workload'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'build-workload'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'build-kernel'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'build-kernel'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'common'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'common'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'crt'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'crt'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'link'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'link'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'targets'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'targets'}:ro",
        "-v",
        f"{resolve_tsvc_src_root(root)}:{CONTAINER_TSVC_SRC_ROOT}:ro",
        image,
    ]
    docker_cmd.extend(
        [
            "bash",
            "-lc",
            (
                f"cd {shlex.quote(str(CONTAINER_EMULATOR_ROOT))} && "
                f"python3 {shlex.quote(str(RUN_SIM_PATH))} "
                f"--simul={shlex.quote(sim_config.simul)} "
                f"--gem5-target={shlex.quote(sim_config.gem5_target)} "
                f"--rtl-target={shlex.quote(sim_config.rtl_target)} "
                f"{shlex.quote(str(CONTAINER_PROJECT_ROOT / source.relative_to(root)))} "
                f"--len={len_1d} --lmul={lmul} "
                f"{f'--use-vf={shlex.quote(use_vf)} ' if use_vf else ''}"
                f"--timeout={effective_timeout} "
                f"--log-dir={shlex.quote(str(CONTAINER_OUTPUT_ROOT / 'logs'))} "
                f"--build-out-dir={shlex.quote(str(CONTAINER_BUILD_OUTPUT_ROOT))}"
                f"{f' --cflags={shlex.quote(extra_cflags)}' if extra_cflags else ''}"
                f"{f' --optflags={shlex.quote(extra_opt_flags)}' if extra_opt_flags else ''}"
            ),
        ]
    )
    return docker_cmd


def run_emulate(
    *,
    bench: str,
    image: str = DEFAULT_IMAGE,
    len_1d: int = 4096,
    lmul: int = 1,
    use_vf: str = "",
    timeout_s: int = 120,
    log_root: str = DEFAULT_LOG_ROOT,
    ensure_image: bool = True,
    extra_cflags: str = "",
    extra_opt_flags: str = "",
    simul: str | None = None,
    gem5_target: str | None = None,
    rtl_target: str | None = None,
) -> dict[str, object]:
    validate_positive_int("len", len_1d)
    validate_positive_int("lmul", lmul)
    validate_vplan_use_vf(use_vf)

    root = repo_root()
    try:
        source = resolve_benchmark_input(root, bench)
    except (FileNotFoundError, benchmark_sources.ConversionError) as exc:
        raise RuntimeError(str(exc)) from exc
    return run_emulate_source(
        benchmark=bench,
        source=source,
        image=image,
        len_1d=len_1d,
        lmul=lmul,
        use_vf=use_vf,
        timeout_s=timeout_s,
        log_root=log_root,
        ensure_image=ensure_image,
        extra_cflags=extra_cflags,
        extra_opt_flags=extra_opt_flags,
        simul=simul,
        gem5_target=gem5_target,
        rtl_target=rtl_target,
    )


def run_emulate_source(
    *,
    benchmark: str,
    source: str | Path,
    image: str = DEFAULT_IMAGE,
    len_1d: int = 4096,
    lmul: int = 1,
    use_vf: str = "",
    timeout_s: int = 120,
    log_root: str = DEFAULT_LOG_ROOT,
    ensure_image: bool = True,
    extra_cflags: str = "",
    extra_opt_flags: str = "",
    simul: str | None = None,
    gem5_target: str | None = None,
    rtl_target: str | None = None,
) -> dict[str, object]:
    validate_positive_int("len", len_1d)
    validate_positive_int("lmul", lmul)
    validate_vplan_use_vf(use_vf)
    sim_config = resolve_simulator_config(
        simul=simul,
        gem5_target=gem5_target,
        rtl_target=rtl_target,
    )

    root = repo_root()
    try:
        resolved_source = resolve_source_path(root, source)
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc
    validate_source_suffix(resolved_source)
    if ensure_image:
        ensure_image_exists(image)
    effective_timeout = resolve_timeout(timeout_s, sim_config)

    resolved_log_root = resolve_log_root(root, log_root)
    out_dir = timestamp_dir(resolved_log_root, benchmark)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"
    summary_file = out_dir / "summary.json"
    report_file = out_dir / "report.md"

    docker_cmd = build_emulate_docker_command(
        root=root,
        out_dir=out_dir,
        source=resolved_source,
        sim_config=sim_config,
        image=image,
        len_1d=len_1d,
        lmul=lmul,
        use_vf=use_vf,
        effective_timeout=effective_timeout,
        extra_cflags=extra_cflags,
        extra_opt_flags=extra_opt_flags,
    )

    docker_command = shlex.join(docker_cmd)
    command_file.write_text(f"{docker_command}\n", encoding="utf-8")

    result = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = (result.stdout or "") + (result.stderr or "")
    container_log.write_text(combined_output, encoding="utf-8")

    parsed = parse_run_sim_output(combined_output)
    run_detail_path = (
        map_container_output_path(str(parsed["run_detail_path"]), out_dir)
        if "run_detail_path" in parsed
        else None
    )
    trace_file = (
        map_container_output_path(str(parsed["trace_file"]), out_dir)
        if "trace_file" in parsed
        else None
    )
    run_detail = run_detail_path.read_text(encoding="utf-8") if run_detail_path and run_detail_path.exists() else ""
    artifact_texts = load_build_artifact_texts(
        out_dir,
        str(parsed.get("built_workload") or ""),
        asm_outputs=[
            str(value)
            for value in parsed.get("asm_outputs", [])
            if isinstance(value, str)
        ],
        ir_outputs=[
            str(value)
            for value in parsed.get("ir_outputs", [])
            if isinstance(value, str)
        ],
    )

    summary: dict[str, object] = {
        "benchmark": benchmark,
        "image": image,
        "simul": sim_config.simul,
        "simulator_target": sim_config.simulator_target,
        "gem5_target": sim_config.gem5_target,
        "rtl_target": sim_config.rtl_target,
        "len_1d": len_1d,
        "lmul": lmul,
        "use_vf": use_vf,
        "timeout_s": timeout_s,
        "effective_timeout_s": effective_timeout,
        "docker_exit_code": result.returncode,
        "status": parsed.get("status", "OK" if result.returncode == 0 else f"EXIT:{result.returncode}"),
        "exit_code": parsed.get("exit_code", result.returncode),
        "wall_time_s": parsed.get("wall_time_s"),
        "kernel_cycles": parsed.get("kernel_cycles"),
        "total_cycles": parsed.get("total_cycles"),
        "sim_speed_khz": parsed.get("sim_speed_khz"),
        "artifact_dir": str(out_dir),
        "container_log": str(container_log),
        "run_detail_path": str(run_detail_path) if run_detail_path else None,
        "trace_file": str(trace_file) if trace_file else None,
        "report_file": str(report_file),
        "docker_command": docker_command,
        "source": str(resolved_source),
    }

    report_text = build_markdown_report(summary)
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_file.write_text(report_text, encoding="utf-8")

    status_text = str(summary.get("status", ""))
    failed = result.returncode != 0 or status_text.startswith(("FAIL", "EXIT", "ASSERT", "TIMEOUT"))

    return {
        "summary": summary,
        "summary_file": str(summary_file),
        "report_text": report_text,
        "container_log_text": combined_output,
        "run_detail": run_detail,
        **artifact_texts,
        "failed": failed,
    }


def main() -> None:
    args = parse_args()
    try:
        if args.bench:
            result = run_emulate(
                bench=args.bench,
                image=args.image,
                len_1d=args.len,
                lmul=args.lmul,
                use_vf=args.use_vf,
                timeout_s=args.timeout,
                log_root=args.log_root,
                extra_cflags=args.extra_cflags,
                extra_opt_flags=args.extra_opt_flags,
                simul=args.simul,
                gem5_target=args.gem5_target,
                rtl_target=args.rtl_target,
            )
        else:
            source = resolve_source_path(repo_root(), args.source)
            validate_source_suffix(source)
            result = run_emulate_source(
                benchmark=benchmark_name_for_input(source),
                source=source,
                image=args.image,
                len_1d=args.len,
                lmul=args.lmul,
                use_vf=args.use_vf,
                timeout_s=args.timeout,
                log_root=args.log_root,
                extra_cflags=args.extra_cflags,
                extra_opt_flags=args.extra_opt_flags,
                simul=args.simul,
                gem5_target=args.gem5_target,
                rtl_target=args.rtl_target,
            )
    except (FileNotFoundError, RuntimeError) as exc:
        fail(str(exc))
    print_summary(result["summary"])
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
