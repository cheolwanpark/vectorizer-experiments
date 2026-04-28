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
    import llvm_pipeline
except ModuleNotFoundError:
    from scripts import benchmark_sources, llvm_pipeline

DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_OUTPUT_ROOT = "artifacts/vplan-explain"
CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_LLVM_CUSTOM_ROOT = Path("/workspace/llvm-custom")
CONTAINER_RUN_COMMON_ROOT = CONTAINER_PROJECT_ROOT / "emulator" / "run" / "common"
CONTAINER_TSVC_SRC_ROOT = CONTAINER_PROJECT_ROOT / "emulator" / "benchmarks" / "TSVC_2" / "src"
VPLAN_EXPLAIN_ARGS = "-passes=loop-vectorize -vplan-explain -disable-output"
VPLAN_LINE_RE = re.compile(r"^LV:\s+VF=(.+?)\s+cost=([^\s]+)(?:\s+compare=([^\s]+))?\s*$")
VPLAN_PLAN_RE = re.compile(r"^LV:\s+VPlan\[(\d+)\]\s+VFs=\{(.+)\}\s*$")
VPLAN_SELECTED_RE = re.compile(r"^LV:\s+selected VF=(.+?)\s+plan=(\d+)\s*$")
CXX_SOURCE_SUFFIXES = {".cc", ".cpp", ".cxx"}


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run vplan-explain for one catalog workload inside Docker."
    )
    parser.add_argument("--bench", required=True, help="Workload id, for example s000")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--platform", default=DEFAULT_PLATFORM, help="Docker platform")
    parser.add_argument("--arch", default="RVV", choices=["RVV", "MAC", "INTEL"], help="Target architecture")
    parser.add_argument("--x86-march", default=llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH, help="x86 -march value (for ARCH=INTEL)")
    parser.add_argument("--vlen", type=int, default=128, help="RVV vector length in bits")
    parser.add_argument("--len", dest="len_1d", type=int, default=llvm_pipeline.DEFAULT_LEN_1D, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=llvm_pipeline.DEFAULT_LMUL, help="LMUL value")
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
    parser.add_argument(
        "--extra-cflags",
        default="",
        help="Extra flags passed to clang (e.g. '-mllvm -riscv-v-precise-mem-cost')",
    )
    parser.add_argument(
        "--extra-opt-flags",
        default="",
        help="Extra flags passed to opt (e.g. '-precise-mem-cost')",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.arch == "RVV" and args.vlen <= 0:
        fail("vlen must be a positive integer")
    if args.len_1d <= 0:
        fail("len must be a positive integer")
    if args.lmul <= 0:
        fail("lmul must be a positive integer")


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
    for tool in ("clang", "opt"):
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


def _container_project_path(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    return CONTAINER_PROJECT_ROOT / resolved_path.relative_to(resolved_root)


def build_compile_flags(
    *,
    root: Path,
    workload: benchmark_sources.CatalogWorkload,
    arch: str,
    len_1d: int,
    lmul: int,
    x86_march: str,
    extra_cflags: str,
) -> list[str]:
    source_path = workload.analysis_source_path
    if workload.kind == "manifest":
        compile_flags = llvm_pipeline.build_vplan_compile_flags(
            run_common_include=CONTAINER_RUN_COMMON_ROOT,
            arch=arch,
            len_1d=len_1d,
            lmul=lmul,
            x86_march=x86_march,
        )
        for include_dir in workload.include_dirs:
            compile_flags.extend(["-I", str(_container_project_path(root, include_dir))])
        compile_flags.extend(workload.llvm_flags)
        compile_flags.extend(workload.compile_flags)
        if extra_cflags:
            compile_flags.extend(extra_cflags.split())
        if source_path is not None and source_path.suffix in CXX_SOURCE_SUFFIXES:
            compile_flags.extend(
                (
                    "-std=gnu++17",
                    "-fno-exceptions",
                    "-fno-rtti",
                    "-fno-threadsafe-statics",
                    "-fno-use-cxa-atexit",
                )
            )
        return compile_flags

    return llvm_pipeline.build_vplan_compile_flags(
        run_common_include=CONTAINER_RUN_COMMON_ROOT,
        tsvc_include=CONTAINER_TSVC_SRC_ROOT,
        arch=arch,
        len_1d=len_1d,
        lmul=lmul,
        x86_march=x86_march,
        extra_cflags=extra_cflags,
    )


def build_opt_flags(
    *,
    workload: benchmark_sources.CatalogWorkload,
    extra_opt_flags: str,
) -> list[str]:
    opt_flags = list(workload.opt_flags) if workload.kind == "manifest" else []
    if extra_opt_flags:
        opt_flags.extend(extra_opt_flags.split())
    return opt_flags


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
    len_1d: int = llvm_pipeline.DEFAULT_LEN_1D,
    lmul: int = llvm_pipeline.DEFAULT_LMUL,
    llvm_custom: str = "",
    vf_use: str = "",
    output_root: str = DEFAULT_OUTPUT_ROOT,
    ensure_image: bool = True,
    echo_output: bool = False,
    x86_march: str = llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH,
    extra_cflags: str = "",
    extra_opt_flags: str = "",
) -> dict[str, object]:
    args = argparse.Namespace(
        bench=bench,
        image=image,
        platform=platform,
        arch=arch,
        vlen=vlen,
        len_1d=len_1d,
        lmul=lmul,
        llvm_custom=llvm_custom,
        vf_use=vf_use,
        output_root=output_root,
    )
    validate_args(args)
    if ensure_image:
        ensure_image_exists(image)

    root = repo_root()
    try:
        workload = benchmark_sources.resolve_catalog_workload(root, bench)
    except FileNotFoundError as exc:
        return {
            "bench": bench,
            "exit_code": 1,
            "output_dir": "",
            "source": "",
            "source_kind": "",
            "function_name": "",
            "analysis_failure": "",
            "analysis_failure_message": "",
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
            "analysis_failure": "",
            "analysis_failure_message": "",
            "container_log": "",
            "container_log_text": str(exc),
            "vplan_log": "",
            "vplan_log_text": "",
            "prevec_ir": "",
            "docker_command": "",
            "vf_candidates": [],
        }

    source_path = workload.analysis_source_path
    if workload.kind == "manifest" and source_path is None:
        return {
            "bench": bench,
            "exit_code": 0,
            "output_dir": "",
            "source": str(workload.manifest_path or workload.primary_source_path or ""),
            "source_kind": workload.source_kind,
            "function_name": workload.function_name,
            "analysis_failure": workload.analysis_failure,
            "analysis_failure_message": workload.analysis_failure_message,
            "container_log": "",
            "container_log_text": "",
            "vplan_log": "",
            "vplan_log_text": "",
            "prevec_ir": "",
            "docker_command": "",
            "vf_candidates": [],
        }
    if source_path is None:
        return {
            "bench": bench,
            "exit_code": 1,
            "output_dir": "",
            "source": "",
            "source_kind": workload.source_kind,
            "function_name": workload.function_name,
            "analysis_failure": "",
            "analysis_failure_message": "",
            "container_log": "",
            "container_log_text": f"analysis source not found for {bench}",
            "vplan_log": "",
            "vplan_log_text": "",
            "prevec_ir": "",
            "docker_command": "",
            "vf_candidates": [],
        }

    llvm_custom_dir = resolve_llvm_custom(root, llvm_custom)
    out_dir = resolve_output_dir(root, output_root, bench)

    vplan_log = out_dir / "vplan-explain.log"
    container_log = out_dir / "container.log"
    command_file = out_dir / "command.txt"

    container_source = _container_project_path(root, source_path)
    container_vplan_log = CONTAINER_OUTPUT_ROOT / vplan_log.name
    container_pipeline_helper = CONTAINER_PROJECT_ROOT / "scripts" / "llvm_pipeline.py"

    forced_vf_arg = f"-vplan-use-vf={shlex.quote(vf_use)}" if vf_use else ""
    compile_flags = build_compile_flags(
        root=root,
        workload=workload,
        arch=arch,
        len_1d=len_1d,
        lmul=lmul,
        x86_march=x86_march,
        extra_cflags=extra_cflags,
    )
    compile_flag_args = " ".join(
        f"--compile-flag={shlex.quote(flag)}" for flag in compile_flags
    )
    opt_flag_args = " ".join(shlex.quote(flag) for flag in build_opt_flags(
        workload=workload,
        extra_opt_flags=extra_opt_flags,
    ))
    if llvm_custom_dir is not None:
        clang_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "clang"))
        opt_cmd = shlex.quote(str(CONTAINER_LLVM_CUSTOM_ROOT / "opt"))
    else:
        clang_cmd = '$(command -v clang-vplan || command -v clang)'
        opt_cmd = '$(command -v opt-vplan || command -v opt)'

    inner_cmd = "\n".join(
        [
            "set -eu",
            f'CLANG_BIN="{clang_cmd}"',
            f'OPT_BIN="{opt_cmd}"',
            'PREVEC_LL="$(mktemp /tmp/vplan-prevec-XXXXXX.ll)"',
            f'python3 {shlex.quote(str(container_pipeline_helper))} emit-prevec '
            f'--source {shlex.quote(str(container_source))} '
            f'--prevec-ll "$PREVEC_LL" '
            f'--clang-bin "$CLANG_BIN" '
            f'--opt-bin "$OPT_BIN" '
            f'--prevec-passes {shlex.quote(workload.prevec_passes or llvm_pipeline.PREVEC_PASSES)} '
            f'{compile_flag_args}',
            f'"$OPT_BIN" {opt_flag_args} {VPLAN_EXPLAIN_ARGS} {forced_vf_arg} "$PREVEC_LL" 2>&1 | tee {shlex.quote(str(container_vplan_log))}',
            'rm -f "$PREVEC_LL"',
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
        "source_kind": workload.source_kind,
        "function_name": workload.function_name,
        "analysis_failure": workload.analysis_failure,
        "analysis_failure_message": workload.analysis_failure_message,
        "container_log": str(container_log),
        "container_log_text": combined_output,
        "vplan_log": str(vplan_log),
        "vplan_log_text": vplan_log_text,
        "prevec_ir": "",
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
        len_1d=args.len_1d,
        lmul=args.lmul,
        llvm_custom=args.llvm_custom,
        vf_use=args.vf_use,
        output_root=args.output_root,
        echo_output=args.verbose,
        x86_march=args.x86_march,
        extra_cflags=args.extra_cflags,
        extra_opt_flags=args.extra_opt_flags,
    )
    if int(result["exit_code"]) != 0:
        container_log = str(result.get("container_log") or "").strip()
        if container_log:
            fail(f"vplan-explain failed; see {container_log}", exit_code=1)
        fail(str(result.get("container_log_text") or "vplan-explain failed"), exit_code=1)
    print(f"{result['bench']}: {len(result['vf_candidates'])} VF(s)")


if __name__ == "__main__":
    main()
