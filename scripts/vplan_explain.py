#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import benchmark_sources
except ModuleNotFoundError:
    from scripts import benchmark_sources

DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_OUTPUT_ROOT = "artifacts/vplan-explain"
CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_LLVM_CUSTOM_ROOT = Path("/workspace/llvm-custom")
CONTAINER_RUN_COMMON_ROOT = CONTAINER_PROJECT_ROOT / "emulator" / "run" / "common"
RVV_IR_TARGET_TRIPLE = "riscv64-unknown-unknown-elf"
RVV_IR_TARGET_DATALAYOUT = "e-m:e-p:64:64-i64:64-i128:128-n32:64-S128"
PREVEC_ARGS = (
    "-passes=mem2reg,instcombine,simplifycfg,loop-simplify,"
    "lcssa,indvars,loop-rotate,instcombine,simplifycfg"
)
VPLAN_EXPLAIN_ARGS = "-passes=loop-vectorize -vplan-explain -disable-output"
VPLAN_LINE_RE = re.compile(r"^LV:\s+VF=(.+?)\s+cost=([^\s]+)(?:\s+compare=([^\s]+))?\s*$")
VPLAN_PLAN_RE = re.compile(r"^LV:\s+VPlan\[(\d+)\]\s+VFs=\{(.+)\}\s*$")
VPLAN_SELECTED_RE = re.compile(r"^LV:\s+selected VF=(.+?)\s+plan=(\d+)\s*$")


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TSVC_2 vplan-explain inside Docker with a standalone root-level wrapper."
    )
    parser.add_argument("--bench", required=True, help="Benchmark name, for example s000")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="Docker platform")
    parser.add_argument("--arch", default="RVV", choices=["RVV", "MAC"], help="Target architecture")
    parser.add_argument("--vlen", type=int, default=128, help="RVV vector length in bits")
    parser.add_argument(
        "--llvm-custom",
        default="",
        help="Optional host LLVM build/bin directory to mount and prefer inside the container.",
    )
    parser.add_argument(
        "--vf-use",
        default="",
        help="Optional forced VF value passed as -vplan-use-vf=...",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Host output root for generated IR and logs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream full vplan-explain output to stdout while still writing logs",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.arch == "RVV" and args.vlen <= 0:
        fail("vlen must be a positive integer")


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


def resolve_llvm_custom(root: Path, llvm_custom: str) -> Path | None:
    if not llvm_custom:
        return None
    path = Path(llvm_custom)
    if not path.is_absolute():
        path = (root / path).resolve()
    if not path.exists():
        fail(f"LLVM_CUSTOM path not found: {path}")
    if path.is_file():
        path = path.parent
    for tool in ("clang", "opt", "llvm-extract"):
        if not (path / tool).exists():
            fail(f"LLVM_CUSTOM is missing {tool}: {path / tool}")
    return path


def resolve_output_dir(root: Path, output_root: str, func: str) -> Path:
    base = Path(output_root)
    if not base.is_absolute():
        base = (root / base).resolve()
    out_dir = base / func
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def format_arch_opt_args(arch: str, vlen: int) -> str:
    if arch != "RVV":
        return ""
    return (
        f"-mtriple=riscv64-unknown-elf -mcpu=generic-rv64 -mattr=+v "
        f"-riscv-v-vector-bits-min={vlen} -riscv-v-vector-bits-max={vlen}"
    )


def run_container_and_capture(
    command: list[str],
    log_path: Path,
    *,
    echo_output: bool = False,
) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    combined_output = (result.stdout or "") + (result.stderr or "")
    log_path.write_text(combined_output, encoding="utf-8")
    if echo_output and combined_output:
        sys.stdout.write(combined_output)
        if not combined_output.endswith("\n"):
            sys.stdout.write("\n")
    return result.returncode, combined_output


def normalize_vplan_vf(raw_vf: str) -> str | None:
    text = raw_vf.strip()
    if not text:
        return None
    scalable_match = re.fullmatch(r"vscale x ([0-9]+)", text)
    if scalable_match:
        return f"scalable:{int(scalable_match.group(1))}"
    fixed_match = re.fullmatch(r"[0-9]+", text)
    if fixed_match:
        return f"fixed:{int(text)}"
    return None


def parse_vplan_vfs(text: str) -> list[dict[str, object]]:
    current_plan: int | None = None
    selected_raw: str | None = None
    selected_plan: int | None = None
    parsed: list[dict[str, object]] = []
    seen: set[str] = set()

    for line in text.splitlines():
        plan_match = VPLAN_PLAN_RE.match(line)
        if plan_match:
            current_plan = int(plan_match.group(1))
            continue

        selected_match = VPLAN_SELECTED_RE.match(line)
        if selected_match:
            selected_raw = selected_match.group(1).strip()
            selected_plan = int(selected_match.group(2))
            continue

        vf_match = VPLAN_LINE_RE.match(line)
        if not vf_match:
            continue

        raw_vf = vf_match.group(1).strip()
        normalized = normalize_vplan_vf(raw_vf)
        if normalized is None or normalized in seen:
            continue

        seen.add(normalized)
        parsed.append(
            {
                "raw_vf": raw_vf,
                "use_vf": normalized,
                "cost": vf_match.group(2).strip(),
                "compare": (vf_match.group(3) or "").strip(),
                "plan_index": current_plan,
                "selected": False,
            }
        )

    for candidate in parsed:
        candidate["selected"] = (
            candidate["raw_vf"] == selected_raw and candidate["plan_index"] == selected_plan
        )

    return parsed


def run_vplan_explain(
    *,
    bench: str,
    image: str = DEFAULT_IMAGE,
    platform: str = DEFAULT_PLATFORM,
    arch: str = "RVV",
    vlen: int = 128,
    llvm_custom: str = "",
    vf_use: str = "",
    output_root: str = DEFAULT_OUTPUT_ROOT,
    ensure_image: bool = True,
    echo_output: bool = False,
) -> dict[str, object]:
    args = argparse.Namespace(
        bench=bench,
        image=image,
        platform=platform,
        arch=arch,
        vlen=vlen,
        llvm_custom=llvm_custom,
        vf_use=vf_use,
        output_root=output_root,
    )
    validate_args(args)
    if ensure_image:
        ensure_image_exists(image)

    root = repo_root()
    try:
        benchmark = benchmark_sources.resolve_benchmark_source(root, bench)
    except FileNotFoundError as exc:
        return {
            "bench": bench,
            "exit_code": 1,
            "output_dir": "",
            "source": "",
            "source_kind": "",
            "function_name": "",
            "container_log": "",
            "container_log_text": str(exc),
            "vplan_log": "",
            "vplan_log_text": "",
            "prevec_ir": "",
            "docker_command": "",
            "vf_candidates": [],
        }
    except benchmark_sources.ConversionError as exc:
        return {
            "bench": bench,
            "exit_code": 1,
            "output_dir": "",
            "source": "",
            "source_kind": "",
            "function_name": "",
            "container_log": "",
            "container_log_text": str(exc),
            "vplan_log": "",
            "vplan_log_text": "",
            "prevec_ir": "",
            "docker_command": "",
            "vf_candidates": [],
        }
    source_path = benchmark.source_path
    llvm_custom_dir = resolve_llvm_custom(root, llvm_custom)
    out_dir = resolve_output_dir(root, output_root, bench)

    full_ll = out_dir / "full.ll"
    raw_ll = out_dir / f"{bench}.ll"
    prevec_ll = out_dir / f"{bench}.prevec.ll"
    vplan_log = out_dir / "vplan-explain.log"
    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"

    container_source = CONTAINER_PROJECT_ROOT / source_path.relative_to(root)
    container_full_ll = CONTAINER_OUTPUT_ROOT / full_ll.name
    container_raw_ll = CONTAINER_OUTPUT_ROOT / raw_ll.name
    container_prevec_ll = CONTAINER_OUTPUT_ROOT / prevec_ll.name
    container_vplan_log = CONTAINER_OUTPUT_ROOT / vplan_log.name
    container_helper = CONTAINER_PROJECT_ROOT / "scripts" / "sanitize_ir.py"

    arch_opt_args = format_arch_opt_args(arch, vlen)
    forced_vf_arg = f"-vplan-use-vf={shlex.quote(vf_use)}" if vf_use else ""
    compile_include_args = shlex.join(["-I", str(CONTAINER_RUN_COMMON_ROOT)])
    if llvm_custom_dir is not None:
        clang_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "clang"))
        opt_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "opt"))
        llvm_extract_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "llvm-extract"))
    else:
        clang_cmd = '$(command -v clang-vplan || command -v clang)'
        opt_cmd = '$(command -v opt-vplan || command -v opt)'
        llvm_extract_cmd = '$(command -v llvm-extract-vplan || command -v llvm-extract)'

    inner_cmd = "\n".join(
        [
            "set -eu",
            f'CLANG_BIN="{clang_cmd}"',
            f'OPT_BIN="{opt_cmd}"',
            f'LLVM_EXTRACT_BIN="{llvm_extract_cmd}"',
            f'"$CLANG_BIN" -O0 -Xclang -disable-O0-optnone -S -emit-llvm '
            f'{compile_include_args} '
            f'{shlex.quote(str(container_source))} -o {shlex.quote(str(container_full_ll))}',
            f'"$LLVM_EXTRACT_BIN" -S --func={shlex.quote(benchmark.function_name)} '
            f'{shlex.quote(str(container_full_ll))} -o {shlex.quote(str(container_raw_ll))}',
            (
                f'python3 {shlex.quote(str(container_helper))} '
                f'--input {shlex.quote(str(container_raw_ll))} '
                f'--output {shlex.quote(str(container_raw_ll))} '
                f'--triple {shlex.quote(RVV_IR_TARGET_TRIPLE)} '
                f'--datalayout {shlex.quote(RVV_IR_TARGET_DATALAYOUT)}'
            )
            if arch == "RVV"
            else ":",
            f'"$OPT_BIN" {arch_opt_args} {PREVEC_ARGS} -S '
            f'{shlex.quote(str(container_raw_ll))} -o {shlex.quote(str(container_prevec_ll))} >/dev/null 2>/dev/null',
            f'"$OPT_BIN" {arch_opt_args} {VPLAN_EXPLAIN_ARGS} {forced_vf_arg} '
            f'<{shlex.quote(str(container_prevec_ll))} 2>&1 | tee {shlex.quote(str(container_vplan_log))}',
            f'printf "\\ngenerated %s\\n" {shlex.quote(str(container_prevec_ll))}',
        ]
    )

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--platform",
        platform,
        "-v",
        f"{root}:{CONTAINER_PROJECT_ROOT}:ro",
        "-v",
        f"{out_dir}:{CONTAINER_OUTPUT_ROOT}",
    ]
    if llvm_custom_dir is not None:
        docker_cmd.extend(
            [
                "-v",
                f"{llvm_custom_dir}:{CONTAINER_LLVM_CUSTOM_ROOT}:ro",
            ]
        )
    docker_cmd.extend(
        [
            image,
            "bash",
            "-lc",
            inner_cmd,
        ]
    )

    docker_command = shlex.join(docker_cmd)
    command_file.write_text(f"{docker_command}\n", encoding="utf-8")
    exit_code, combined_output = run_container_and_capture(
        docker_cmd,
        container_log,
        echo_output=echo_output,
    )
    vplan_log_text = vplan_log.read_text(encoding="utf-8") if vplan_log.exists() else ""
    return {
        "bench": bench,
        "exit_code": exit_code,
        "output_dir": str(out_dir),
        "source": str(source_path),
        "source_kind": benchmark.source_kind,
        "function_name": benchmark.function_name,
        "container_log": str(container_log),
        "container_log_text": combined_output,
        "vplan_log": str(vplan_log),
        "vplan_log_text": vplan_log_text,
        "prevec_ir": str(prevec_ll),
        "docker_command": docker_command,
        "vf_candidates": parse_vplan_vfs(vplan_log_text or combined_output),
    }


def main() -> None:
    args = parse_args()
    result = run_vplan_explain(
        bench=args.bench,
        image=args.image,
        platform=args.platform,
        arch=args.arch,
        vlen=args.vlen,
        llvm_custom=args.llvm_custom,
        vf_use=args.vf_use,
        output_root=args.output_root,
        echo_output=args.verbose,
    )
    if int(result["exit_code"]) != 0:
        container_log = str(result.get("container_log") or "").strip()
        if container_log:
            fail(f"vplan-explain failed; see {container_log}", exit_code=1)
        fail(str(result.get("container_log_text") or "vplan-explain failed"), exit_code=1)
    print(f"{result['bench']}: {len(result['vf_candidates'])} VF(s)")


if __name__ == "__main__":
    main()
