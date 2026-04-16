#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

try:
    import benchmark_sources
    import emulate
    import llvm_pipeline
    import vplan_explain
except ModuleNotFoundError:
    from scripts import benchmark_sources, emulate, llvm_pipeline, vplan_explain


DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_LOG_ROOT = "artifacts/profile"
DEFAULT_WARMUP = 3
DEFAULT_REPEAT = 10
KC_RE = re.compile(r"^KC=(\d+)$", re.MULTILINE)

CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_BUILD_DIR = CONTAINER_OUTPUT_ROOT / "build"
CONTAINER_RUN_COMMON = CONTAINER_PROJECT_ROOT / "emulator" / "run" / "common"
CONTAINER_TSVC_SRC = CONTAINER_PROJECT_ROOT / "emulator" / "benchmarks" / "TSVC_2" / "src"
CONTAINER_PROFILER = CONTAINER_PROJECT_ROOT / "profiler"
CONTAINER_PIPELINE_HELPER = CONTAINER_PROJECT_ROOT / "scripts" / "llvm_pipeline.py"
CONTAINER_LLVM_CUSTOM_ROOT = Path("/workspace/llvm-custom")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile a TSVC kernel on x86 using RDTSC cycle measurement (compiled inside Docker)."
    )
    parser.add_argument("--bench", required=True, help="Benchmark name, for example s000")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--len", dest="len_1d", type=int, default=llvm_pipeline.DEFAULT_LEN_1D, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=llvm_pipeline.DEFAULT_LMUL, help="LMUL value")
    parser.add_argument("--use-vf", default="", help="Force VF, e.g. fixed:4 or scalable:2")
    parser.add_argument("--llvm-custom", default="", help="Host LLVM build/bin directory")
    parser.add_argument("--x86-march", default=llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH, help="x86 -march value")
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP, help="Warmup iterations")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="Timed iterations")
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT, help="Host output root")
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang")
    return parser.parse_args()


def build_inner_script(
    *,
    container_source: Path,
    compile_flag_args: str,
    use_vf: str,
    len_1d: int,
    lmul: int,
    warmup: int,
    repeat: int,
    is_generated: bool,
    llvm_custom_dir: Path | None,
) -> str:
    if llvm_custom_dir is not None:
        clang_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "clang"))
        opt_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "opt"))
        llc_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "llc"))
    else:
        clang_cmd = '$(command -v clang-vplan || command -v clang)'
        opt_cmd = '$(command -v opt-vplan || command -v opt)'
        llc_cmd = '$(command -v llc-vplan || command -v llc)'

    defines = f"-DLEN_1D={len_1d} -DLEN_2D=32 -DLMUL={lmul}"
    build = str(CONTAINER_BUILD_DIR)
    use_vf_arg = f"--use-vf={shlex.quote(use_vf)}" if use_vf else ""
    opt_log_arg = f"--opt-log={build}/opt.log" if use_vf else ""

    lines = [
        "set -eu",
        f'CLANG="{clang_cmd}"',
        f'OPT="{opt_cmd}"',
        f'LLC="{llc_cmd}"',
        f"mkdir -p {build}",
        "",
        "# 1. Compile kernel through LLVM pipeline",
        f"python3 {shlex.quote(str(CONTAINER_PIPELINE_HELPER))} build-artifacts "
        f"--source {shlex.quote(str(container_source))} "
        f"--opt-ll {build}/kernel.opt.ll "
        f"--asm-out {build}/kernel.s "
        f'--obj-out {build}/kernel.o '
        f'--clang-bin "$CLANG" '
        f'--opt-bin "$OPT" '
        f'--llc-bin "$LLC" '
        f"{compile_flag_args} "
        f"{use_vf_arg} {opt_log_arg}".strip(),
        "",
        "# 2. Compile support files",
        f'"$CLANG" -O2 -iquote {shlex.quote(str(CONTAINER_RUN_COMMON))} {defines} '
        f"-c {shlex.quote(str(CONTAINER_PROFILER / 'harness_x86.c'))} -o {build}/harness.o",
        f'"$CLANG" -O2 -iquote {shlex.quote(str(CONTAINER_RUN_COMMON))} {defines} '
        f"-c {shlex.quote(str(CONTAINER_RUN_COMMON / 'arrays.c'))} -o {build}/arrays.o",
    ]

    link_objs = f"{build}/kernel.o {build}/harness.o {build}/arrays.o"
    if is_generated:
        lines.append(
            f'"$CLANG" -O2 -iquote {shlex.quote(str(CONTAINER_RUN_COMMON))} {defines} '
            f"-c {shlex.quote(str(CONTAINER_PROFILER / 'tsvc_runtime_x86.c'))} -o {build}/tsvc_runtime.o"
        )
        link_objs += f" {build}/tsvc_runtime.o"

    perf_events = ",".join([
        "cycles", "instructions",
        "cache-references", "cache-misses",
        "branch-instructions", "branch-misses",
        "L1-dcache-loads", "L1-dcache-load-misses",
        "LLC-loads", "LLC-load-misses",
    ])

    lines.extend([
        "",
        "# 3. Link",
        f'"$CLANG" {link_objs} -lm -o {build}/bench',
        "",
        "# 4. Run (pure RDTSC, no perf overhead)",
        f"{build}/bench --warmup={warmup} --repeat={repeat}",
        "",
        f"# 5. Collect run detail (best of {repeat} perf stat runs)",
        "_BEST_KC=999999999999999",
        "_BEST_RUN=1",
        f"for _i in $(seq 1 {repeat}); do",
        f"  perf stat -e {perf_events} "
        f"{build}/bench --warmup={warmup} --repeat=1 "
        f"> /tmp/perf_run_$_i.txt 2>&1 || true",
        "  _KC=$(grep -m1 '^KC=' /tmp/perf_run_$_i.txt 2>/dev/null"
        " | cut -d= -f2) || true",
        '  if [ -n "$_KC" ] && [ "$_KC" -lt "$_BEST_KC" ] 2>/dev/null; then',
        "    _BEST_KC=$_KC",
        "    _BEST_RUN=$_i",
        "  fi",
        "done",
        "{",
        "  echo '=== CPU ==='",
        "  lscpu | head -20",
        "  echo ''",
        "  echo '=== COMPILER ==='",
        '  "$CLANG" --version | head -3',
        "  echo ''",
        f"  echo '=== PERF STAT (best of {repeat}," " KC='$_BEST_KC') ==='",
        "  cat /tmp/perf_run_$_BEST_RUN.txt",
        f"}} > {build}/run_detail.txt 2>&1",
    ])

    return "\n".join(lines)


def run_profile(
    *,
    bench: str,
    image: str = DEFAULT_IMAGE,
    len_1d: int = llvm_pipeline.DEFAULT_LEN_1D,
    lmul: int = llvm_pipeline.DEFAULT_LMUL,
    use_vf: str = "",
    llvm_custom: str = "",
    x86_march: str = llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH,
    warmup: int = DEFAULT_WARMUP,
    repeat: int = DEFAULT_REPEAT,
    log_root: str = DEFAULT_LOG_ROOT,
    ensure_image: bool = True,
    extra_cflags: str = "",
) -> dict[str, object]:
    emulate.validate_positive_int("len", len_1d)
    emulate.validate_positive_int("lmul", lmul)
    emulate.validate_vplan_use_vf(use_vf)

    root = emulate.repo_root()
    try:
        benchmark = benchmark_sources.resolve_benchmark_source(root, bench)
    except (FileNotFoundError, benchmark_sources.ConversionError) as exc:
        raise RuntimeError(str(exc)) from exc

    if ensure_image:
        emulate.ensure_image_exists(image)

    llvm_custom_dir = vplan_explain.resolve_llvm_custom(root, llvm_custom)

    resolved_log_root = emulate.resolve_log_root(root, log_root)
    out_dir = emulate.timestamp_dir(resolved_log_root, bench)

    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"

    container_source = CONTAINER_PROJECT_ROOT / benchmark.source_path.relative_to(root)

    compile_flags = llvm_pipeline.build_vplan_compile_flags(
        run_common_include=CONTAINER_RUN_COMMON,
        tsvc_include=CONTAINER_TSVC_SRC,
        arch="INTEL",
        len_1d=len_1d,
        lmul=lmul,
        x86_march=x86_march,
        extra_cflags=extra_cflags,
    )
    compile_flag_args = " ".join(
        f"--compile-flag={shlex.quote(flag)}" for flag in compile_flags
    )

    inner_cmd = build_inner_script(
        container_source=container_source,
        compile_flag_args=compile_flag_args,
        use_vf=use_vf,
        len_1d=len_1d,
        lmul=lmul,
        warmup=warmup,
        repeat=repeat,
        is_generated=benchmark.source_kind == "generated",
        llvm_custom_dir=llvm_custom_dir,
    )

    docker_cmd = [
        "docker", "run", "--rm",
        "--platform", DEFAULT_PLATFORM,
        "--cap-add", "SYS_ADMIN",
        "--security-opt", "seccomp=unconfined",
        "-v", f"{root}:{CONTAINER_PROJECT_ROOT}:ro",
        "-v", f"{out_dir}:{CONTAINER_OUTPUT_ROOT}",
    ]
    if llvm_custom_dir is not None:
        docker_cmd.extend(["-v", f"{llvm_custom_dir}:{CONTAINER_LLVM_CUSTOM_ROOT}:ro"])
    docker_cmd.extend([image, "bash", "-lc", inner_cmd])

    docker_command = shlex.join(docker_cmd)
    command_file.write_text(f"{docker_command}\n", encoding="utf-8")

    t0 = time.monotonic()
    result = subprocess.run(docker_cmd, capture_output=True, text=True, check=False)
    wall_time = time.monotonic() - t0
    combined = (result.stdout or "") + (result.stderr or "")
    container_log.write_text(combined, encoding="utf-8")

    kernel_cycles = None
    kc_match = KC_RE.search(combined)
    if kc_match:
        kernel_cycles = int(kc_match.group(1))

    build_dir = out_dir / "build"
    opt_ll_path = build_dir / "kernel.opt.ll"
    asm_path = build_dir / "kernel.s"
    opt_ll_text = opt_ll_path.read_text(encoding="utf-8") if opt_ll_path.exists() else ""
    asm_text = asm_path.read_text(encoding="utf-8") if asm_path.exists() else ""
    run_detail_path = build_dir / "run_detail.txt"
    run_detail = run_detail_path.read_text(encoding="utf-8") if run_detail_path.exists() else ""

    status = "PASS" if result.returncode == 0 and kernel_cycles is not None else f"EXIT:{result.returncode}"

    summary: dict[str, object] = {
        "benchmark": bench,
        "image": image,
        "simulator_target": "x86_native",
        "len_1d": len_1d,
        "lmul": lmul,
        "use_vf": use_vf,
        "timeout_s": None,
        "effective_timeout_s": None,
        "docker_exit_code": result.returncode,
        "status": status,
        "exit_code": result.returncode,
        "wall_time_s": round(wall_time, 3),
        "kernel_cycles": kernel_cycles,
        "total_cycles": kernel_cycles,
        "sim_speed_khz": None,
        "artifact_dir": str(out_dir),
        "container_log": str(container_log),
        "run_detail_path": str(run_detail_path),
        "trace_file": None,
        "report_file": str(out_dir / "report.md"),
        "docker_command": docker_command,
        "source": str(benchmark.source_path),
    }

    report_text = _build_report(summary)
    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(report_text, encoding="utf-8")

    failed = result.returncode != 0 or kernel_cycles is None

    return {
        "summary": summary,
        "summary_file": str(summary_file),
        "report_text": report_text,
        "container_log_text": combined,
        "run_detail": run_detail,
        "opt_ll_text": opt_ll_text,
        "asm_text": asm_text,
        "failed": failed,
    }


def _build_report(summary: dict[str, object]) -> str:
    forced_vf = summary.get("use_vf") or "default"
    lines = [
        f"# Profile Report: `{summary['benchmark']}`",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Target | `{summary['simulator_target']}` |",
        f"| Status | `{summary.get('status', 'unknown')}` |",
        f"| LEN | `{summary['len_1d']}` |",
        f"| LMUL | `{summary['lmul']}` |",
        f"| Forced VF | `{forced_vf}` |",
        f"| Kernel cycles | `{summary.get('kernel_cycles', 'n/a')}` |",
        f"| Wall time (s) | `{summary.get('wall_time_s', 'n/a')}` |",
        "",
    ]
    return "\n".join(lines)


def print_summary(summary: dict[str, object]) -> None:
    forced_vf = summary.get("use_vf") or "default"
    lines = [
        f"Benchmark:  {summary['benchmark']}",
        f"Target:     {summary['simulator_target']}",
        f"Status:     {summary.get('status', 'unknown')}",
        f"Forced VF:  {forced_vf}",
        f"Kernel:     {summary.get('kernel_cycles', 'n/a')} cycles",
        f"Wall time:  {summary.get('wall_time_s', 'n/a')}s",
        f"Artifacts:  {summary['artifact_dir']}",
    ]
    print("\n".join(lines))


def main() -> None:
    args = parse_args()
    try:
        result = run_profile(
            bench=args.bench,
            image=args.image,
            len_1d=args.len_1d,
            lmul=args.lmul,
            use_vf=args.use_vf,
            llvm_custom=args.llvm_custom,
            x86_march=args.x86_march,
            warmup=args.warmup,
            repeat=args.repeat,
            log_root=args.log_root,
            extra_cflags=args.extra_cflags,
        )
    except RuntimeError as exc:
        emulate.fail(str(exc))
    print_summary(result["summary"])
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
