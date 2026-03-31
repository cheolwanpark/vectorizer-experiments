#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from tsvc_helper import resolve_metadata


DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_TSVC_DIR = CONTAINER_PROJECT_ROOT / "benchmarks" / "MultiSource" / "Benchmarks" / "TSVC"
CONTAINER_LLVM_CUSTOM_ROOT = Path("/workspace/llvm-custom")
RVV_IR_TARGET_TRIPLE = "riscv64-unknown-unknown-elf"
RVV_IR_TARGET_DATALAYOUT = "e-m:e-p:64:64-i64:64-i128:128-n32:64-S128"
PREVEC_ARGS = (
    "-passes=mem2reg,instcombine,simplifycfg,loop-simplify,"
    "lcssa,indvars,loop-rotate,instcombine,simplifycfg"
)
VPLAN_EXPLAIN_ARGS = "-passes=loop-vectorize -vplan-explain -disable-output"


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TSVC vplan-explain inside Docker with a standalone root-level wrapper."
    )
    parser.add_argument("--bench", required=True, help="Benchmark name, for example s000")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="Docker platform")
    parser.add_argument("--type", default="dbl", choices=["dbl", "flt"], help="TSVC data type")
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
        default="artifacts/vplan-explain",
        help="Host output root for generated IR and logs",
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


def resolve_output_dir(root: Path, output_root: str, variant: str, func: str) -> Path:
    base = Path(output_root)
    if not base.is_absolute():
        base = (root / base).resolve()
    out_dir = base / variant / func
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def format_arch_opt_args(arch: str, vlen: int) -> str:
    if arch != "RVV":
        return ""
    return (
        f"-mtriple=riscv64-unknown-elf -mcpu=generic-rv64 -mattr=+v "
        f"-riscv-v-vector-bits-min={vlen} -riscv-v-vector-bits-max={vlen}"
    )


def run_container_and_capture(command: list[str], log_path: Path) -> int:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    combined_output = (result.stdout or "") + (result.stderr or "")
    log_path.write_text(combined_output, encoding="utf-8")
    if combined_output:
        sys.stdout.write(combined_output)
        if not combined_output.endswith("\n"):
            sys.stdout.write("\n")
    return result.returncode


def main() -> None:
    args = parse_args()
    validate_args(args)
    ensure_image_exists(args.image)

    root = repo_root()
    tsvc_dir = root / "benchmarks" / "MultiSource" / "Benchmarks" / "TSVC"
    metadata = resolve_metadata(tsvc_dir, args.bench, args.type)
    llvm_custom_dir = resolve_llvm_custom(root, args.llvm_custom)
    out_dir = resolve_output_dir(root, args.output_root, args.type, args.bench)

    full_ll = out_dir / "full.ll"
    raw_ll = out_dir / f"{args.bench}.ll"
    prevec_ll = out_dir / f"{args.bench}.prevec.ll"
    vplan_log = out_dir / "vplan-explain.log"
    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"

    source_path = Path(metadata["source_path"])
    container_source = CONTAINER_PROJECT_ROOT / source_path.relative_to(root)
    container_full_ll = CONTAINER_OUTPUT_ROOT / full_ll.name
    container_raw_ll = CONTAINER_OUTPUT_ROOT / raw_ll.name
    container_prevec_ll = CONTAINER_OUTPUT_ROOT / prevec_ll.name
    container_vplan_log = CONTAINER_OUTPUT_ROOT / vplan_log.name
    container_helper = CONTAINER_PROJECT_ROOT / "scripts" / "tsvc_helper.py"

    arch_opt_args = format_arch_opt_args(args.arch, args.vlen)
    forced_vf_arg = f"-vplan-use-vf={shlex.quote(args.vf_use)}" if args.vf_use else ""
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
            f'{shlex.quote(str(container_source))} -o {shlex.quote(str(container_full_ll))}',
            f'"$LLVM_EXTRACT_BIN" -S --func={shlex.quote(args.bench)} '
            f'{shlex.quote(str(container_full_ll))} -o {shlex.quote(str(container_raw_ll))}',
            (
                f'python3 {shlex.quote(str(container_helper))} sanitize-ir '
                f'--input {shlex.quote(str(container_raw_ll))} '
                f'--output {shlex.quote(str(container_raw_ll))} '
                f'--triple {shlex.quote(RVV_IR_TARGET_TRIPLE)} '
                f'--datalayout {shlex.quote(RVV_IR_TARGET_DATALAYOUT)}'
            )
            if args.arch == "RVV"
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
        args.platform,
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
        args.image,
        "bash",
        "-lc",
        inner_cmd,
        ]
    )

    docker_command = shlex.join(docker_cmd)
    command_file.write_text(f"{docker_command}\n", encoding="utf-8")
    exit_code = run_container_and_capture(docker_cmd, container_log)
    if exit_code != 0:
        fail(f"vplan-explain failed; see {container_log}", exit_code=1)


if __name__ == "__main__":
    main()
