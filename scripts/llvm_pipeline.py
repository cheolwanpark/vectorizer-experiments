#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


PREVEC_PASSES = (
    "mem2reg,instcombine,simplifycfg,loop-simplify,"
    "lcssa,indvars,loop-rotate,instcombine,simplifycfg"
)
DEFAULT_OPT_PASSES = "default<O3>"
DEFAULT_LEN_1D = 4096
DEFAULT_LMUL = 1
DEFAULT_RVV_TARGET_ARCH = "rv64gcv"
DEFAULT_RVV_TARGET_ABI = "lp64d"
DEFAULT_RVV_TARGET_CC_FLAG = "--target=riscv64-unknown-elf"
DEFAULT_INTEL_TARGET_MARCH = "emeraldrapids"
DEFAULT_INTEL_TARGET_TRIPLE = "x86_64-unknown-linux-gnu"


def run_checked(
    command: list[str],
    *,
    description: str,
    log_path: Path | None = None,
) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    combined_output = (result.stdout or "") + (result.stderr or "")
    if log_path is not None:
        log_path.write_text(combined_output, encoding="utf-8")
    if result.returncode != 0:
        message = combined_output.strip() or f"{description} failed with exit code {result.returncode}"
        raise RuntimeError(message)
    return combined_output


def compile_source_to_raw_ir(
    *,
    clang_bin: str,
    source: Path,
    raw_ll: Path,
    compile_flags: list[str],
) -> None:
    run_checked(
        [
            clang_bin,
            *compile_flags,
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
            "-S",
            "-emit-llvm",
            str(source),
            "-o",
            str(raw_ll),
        ],
        description="raw IR generation",
    )


def canonicalize_prevector_ir(
    *,
    opt_bin: str,
    raw_ll: Path,
    prevec_ll: Path,
    prevec_passes: str = PREVEC_PASSES,
) -> None:
    run_checked(
        [
            opt_bin,
            f"-passes={prevec_passes}",
            "-S",
            str(raw_ll),
            "-o",
            str(prevec_ll),
        ],
        description="pre-vector canonicalization",
    )


def optimize_ir(
    *,
    opt_bin: str,
    input_ll: Path,
    output_ll: Path,
    opt_passes: str = DEFAULT_OPT_PASSES,
    use_vf: str = "",
    log_path: Path | None = None,
) -> str:
    command = [
        opt_bin,
        "-pass-remarks=loop-vectorize",
        "-pass-remarks-missed=loop-vectorize",
        "-pass-remarks-analysis=loop-vectorize",
        f"-passes={opt_passes}",
    ]
    if use_vf:
        command.append(f"-vplan-use-vf={use_vf}")
    command.extend(["-S", str(input_ll), "-o", str(output_ll)])
    return run_checked(command, description="LLVM optimization", log_path=log_path)


def lower_to_asm(
    *,
    llc_bin: str,
    input_ll: Path,
    asm_out: Path,
) -> None:
    run_checked(
        [llc_bin, "-O3", "-o", str(asm_out), str(input_ll)],
        description="assembly lowering",
    )


def lower_to_object(
    *,
    llc_bin: str,
    input_ll: Path,
    obj_out: Path,
) -> None:
    run_checked(
        [llc_bin, "-O3", "--filetype=obj", "-o", str(obj_out), str(input_ll)],
        description="object lowering",
    )


def emit_prevector_ir(
    *,
    source: Path,
    prevec_ll: Path,
    clang_bin: str,
    opt_bin: str,
    compile_flags: list[str],
    prevec_passes: str = PREVEC_PASSES,
) -> None:
    with tempfile.TemporaryDirectory(prefix="llvm-pipeline-") as tmp_dir:
        raw_ll = Path(tmp_dir) / "raw.ll"
        compile_source_to_raw_ir(
            clang_bin=clang_bin,
            source=source,
            raw_ll=raw_ll,
            compile_flags=compile_flags,
        )
        canonicalize_prevector_ir(
            opt_bin=opt_bin,
            raw_ll=raw_ll,
            prevec_ll=prevec_ll,
            prevec_passes=prevec_passes,
        )


def build_optimized_artifacts(
    *,
    source: Path,
    opt_ll: Path,
    asm_out: Path,
    obj_out: Path | None,
    clang_bin: str,
    opt_bin: str,
    llc_bin: str,
    compile_flags: list[str],
    use_vf: str = "",
    prevec_passes: str = PREVEC_PASSES,
    opt_passes: str = DEFAULT_OPT_PASSES,
    opt_log: Path | None = None,
) -> None:
    with tempfile.TemporaryDirectory(prefix="llvm-pipeline-") as tmp_dir:
        raw_ll = Path(tmp_dir) / "raw.ll"
        prevec_ll = Path(tmp_dir) / "prevec.ll"
        compile_source_to_raw_ir(
            clang_bin=clang_bin,
            source=source,
            raw_ll=raw_ll,
            compile_flags=compile_flags,
        )
        canonicalize_prevector_ir(
            opt_bin=opt_bin,
            raw_ll=raw_ll,
            prevec_ll=prevec_ll,
            prevec_passes=prevec_passes,
        )
        optimize_ir(
            opt_bin=opt_bin,
            input_ll=prevec_ll,
            output_ll=opt_ll,
            opt_passes=opt_passes,
            use_vf=use_vf,
            log_path=opt_log,
        )
        lower_to_asm(
            llc_bin=llc_bin,
            input_ll=opt_ll,
            asm_out=asm_out,
        )
        if obj_out is not None:
            lower_to_object(
                llc_bin=llc_bin,
                input_ll=opt_ll,
                obj_out=obj_out,
            )


def build_vplan_compile_flags(
    *,
    run_common_include: Path,
    tsvc_include: Path | None = None,
    arch: str = "RVV",
    len_1d: int = DEFAULT_LEN_1D,
    lmul: int = DEFAULT_LMUL,
    x86_march: str = DEFAULT_INTEL_TARGET_MARCH,
    extra_cflags: str = "",
) -> list[str]:
    common = [
        "-fno-builtin",
        "-fno-common",
        f"-DLMUL={lmul}",
        f"-DLEN_1D={len_1d}",
        "-I",
        str(run_common_include),
    ]
    if tsvc_include is not None:
        common.extend(["-I", str(tsvc_include)])
    extra = extra_cflags.split() if extra_cflags else []
    if arch == "RVV":
        return [
            f"-march={DEFAULT_RVV_TARGET_ARCH}",
            f"-mabi={DEFAULT_RVV_TARGET_ABI}",
            DEFAULT_RVV_TARGET_CC_FLAG,
            "-mcmodel=medany",
            "-static",
            "-nostdlib",
            *common,
            "-mllvm",
            f"-riscv-v-register-bit-width-lmul={lmul}",
            *extra,
        ]
    if arch == "INTEL":
        return [
            f"--target={DEFAULT_INTEL_TARGET_TRIPLE}",
            f"-march={x86_march}",
            *common,
            *extra,
        ]
    return [*common, *extra]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shared LLVM pipeline helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build-artifacts")
    build.add_argument("--source", required=True)
    build.add_argument("--opt-ll", required=True)
    build.add_argument("--asm-out", required=True)
    build.add_argument("--obj-out", default="")
    build.add_argument("--clang-bin", required=True)
    build.add_argument("--opt-bin", required=True)
    build.add_argument("--llc-bin", required=True)
    build.add_argument("--use-vf", default="")
    build.add_argument("--prevec-passes", default=PREVEC_PASSES)
    build.add_argument("--opt-passes", default=DEFAULT_OPT_PASSES)
    build.add_argument("--opt-log", default="")
    build.add_argument("--compile-flag", action="append", default=[])

    emit_prevec = subparsers.add_parser("emit-prevec")
    emit_prevec.add_argument("--source", required=True)
    emit_prevec.add_argument("--prevec-ll", required=True)
    emit_prevec.add_argument("--clang-bin", required=True)
    emit_prevec.add_argument("--opt-bin", required=True)
    emit_prevec.add_argument("--prevec-passes", default=PREVEC_PASSES)
    emit_prevec.add_argument("--compile-flag", action="append", default=[])

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "build-artifacts":
        build_optimized_artifacts(
            source=Path(args.source),
            opt_ll=Path(args.opt_ll),
            asm_out=Path(args.asm_out),
            obj_out=Path(args.obj_out) if args.obj_out else None,
            clang_bin=args.clang_bin,
            opt_bin=args.opt_bin,
            llc_bin=args.llc_bin,
            compile_flags=list(args.compile_flag),
            use_vf=args.use_vf,
            prevec_passes=args.prevec_passes,
            opt_passes=args.opt_passes,
            opt_log=Path(args.opt_log) if args.opt_log else None,
        )
        return

    if args.command == "emit-prevec":
        emit_prevector_ir(
            source=Path(args.source),
            prevec_ll=Path(args.prevec_ll),
            clang_bin=args.clang_bin,
            opt_bin=args.opt_bin,
            compile_flags=list(args.compile_flag),
            prevec_passes=args.prevec_passes,
        )
        return

    raise AssertionError(f"unexpected command: {args.command}")


if __name__ == "__main__":
    main()
