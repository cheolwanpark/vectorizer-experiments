#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_PLATFORM = "linux/amd64"
CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_EMULATOR_ROOT = Path("/workspace/emulator")
RUN_SIM_PATH = Path("/workspace/emulator/run-sim.sh")
SIM_TARGET = "xiangshan.KunminghuV2Config"
LEGACY_TIMEOUT_S = 120
XIANSHAN_DEFAULT_TIMEOUT_S = 1800


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one TSVC kernel through XiangShan in Docker and write a host-side report."
    )
    parser.add_argument("--bench", required=True, help="Benchmark name, for example s000")
    parser.add_argument("--image", default="vplan-cost-measure:latest", help="Docker image tag")
    parser.add_argument("--len", type=int, default=4096, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value")
    parser.add_argument("--use-vf", type=int, default=None, help="Force loop vectorization with a fixed VF")
    parser.add_argument("--timeout", type=int, default=120, help="Simulation timeout in seconds")
    parser.add_argument(
        "--log-root",
        default="artifacts/emulate",
        help="Host output root for reports and raw artifacts",
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


def validate_benchmark(root: Path, bench: str) -> Path:
    if not re.fullmatch(r"s\d{3,4}", bench):
        fail(f"invalid benchmark name: {bench}")
    source = root / "emulator" / "run" / "src" / f"{bench}.c"
    if not source.exists():
        fail(f"benchmark source not found: {source}")
    return source


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
            "Build or tag the image first, for example: docker build -t vplan-cost-measure:latest ."
        )


def timestamp_dir(root: Path, bench: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = root / bench / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir


def parse_int(text: str) -> int:
    return int(text.replace(",", ""))


def parse_float(text: str) -> float:
    return float(text.strip())


def resolve_timeout(timeout_s: int) -> int:
    if timeout_s == LEGACY_TIMEOUT_S:
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
        "run_log": (r"^Log file:\s+(.+)$", str),
        "trace_file": (r"^Trace:\s+(.+)$", str),
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


def build_markdown_report(summary: dict[str, object]) -> str:
    forced_vf = summary.get("use_vf") or "default"
    trace_file = summary.get("trace_file", "n/a")
    lines = [
        f"# Emulate Report: `{summary['benchmark']}`",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Simulator target | `{summary['simulator_target']}` |",
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
        f"- Run log: `{summary.get('run_log', 'n/a')}`",
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
    lines = [
        f"Benchmark:  {summary['benchmark']}",
        f"Target:     {summary['simulator_target']}",
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


def main() -> None:
    args = parse_args()
    validate_positive_int("len", args.len)
    validate_positive_int("lmul", args.lmul)
    validate_positive_int("use_vf", args.use_vf)
    root = repo_root()
    source = validate_benchmark(root, args.bench)
    ensure_image_exists(args.image)
    effective_timeout = resolve_timeout(args.timeout)

    log_root = Path(args.log_root)
    if not log_root.is_absolute():
        log_root = (root / log_root).resolve()
    out_dir = timestamp_dir(log_root, args.bench)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"
    summary_file = out_dir / "summary.json"
    report_file = out_dir / "report.md"

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
        f"{root / 'emulator' / 'run' / 'build-kernel'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'build-kernel'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'common'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'common'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'crt'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'crt'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'link'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'link'}:ro",
        "-v",
        f"{root / 'emulator' / 'run' / 'targets'}:{CONTAINER_EMULATOR_ROOT / 'run' / 'targets'}:ro",
        args.image,
        "bash",
        "-lc",
        (
            f"cd {shlex.quote(str(CONTAINER_EMULATOR_ROOT))} && "
            f"python3 {shlex.quote(str(RUN_SIM_PATH))} {SIM_TARGET} "
            f"{shlex.quote(str(CONTAINER_PROJECT_ROOT / source.relative_to(root)))} "
            f"--len={args.len} --lmul={args.lmul} "
            f"{f'--use-vf={args.use_vf} ' if args.use_vf is not None else ''}"
            f"--timeout={effective_timeout} "
            f"--log-dir={shlex.quote(str(CONTAINER_OUTPUT_ROOT / 'logs'))}"
        ),
    ]

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
    run_log = (
        map_container_output_path(str(parsed["run_log"]), out_dir)
        if "run_log" in parsed
        else None
    )
    trace_file = (
        map_container_output_path(str(parsed["trace_file"]), out_dir)
        if "trace_file" in parsed
        else None
    )

    summary: dict[str, object] = {
        "benchmark": args.bench,
        "image": args.image,
        "simulator_target": SIM_TARGET,
        "len_1d": args.len,
        "lmul": args.lmul,
        "use_vf": args.use_vf,
        "timeout_s": args.timeout,
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
        "run_log": str(run_log) if run_log else None,
        "trace_file": str(trace_file) if trace_file else None,
        "report_file": str(report_file),
        "docker_command": docker_command,
        "source": str(source),
    }

    report_text = build_markdown_report(summary)
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_file.write_text(report_text, encoding="utf-8")

    print_summary(summary)

    if result.returncode != 0 or str(summary.get("status", "")).startswith(("FAIL", "EXIT", "ASSERT", "TIMEOUT")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
