#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn


DEFAULT_IMAGE = "vplan-cost-measure:latest"
DEFAULT_PLATFORM = "linux/amd64"
DEFAULT_DB_PATH = "artifacts/microbench.sqlite"
DEFAULT_LOG_ROOT = "artifacts/microbench"
DEFAULT_TIMEOUT = 120
DEFAULT_CONCURRENCY = 1
DEFAULT_TARGET = "xiangshan.KunminghuV2Config"
LEGACY_TIMEOUT_S = 120
XIANSHAN_DEFAULT_TIMEOUT_S = 1800

CONTAINER_PROJECT_ROOT = Path("/workspace/host-project")
CONTAINER_OUTPUT_ROOT = Path("/workspace/output")
CONTAINER_EMULATOR_ROOT = Path("/workspace/emulator")
CONTAINER_RUN_SIM = CONTAINER_EMULATOR_ROOT / "run-sim.sh"
CONTAINER_SIM_CONFIG = CONTAINER_EMULATOR_ROOT / "sim-configs.yaml"
CONTAINER_COMMON_ROOT = CONTAINER_PROJECT_ROOT / "emulator" / "benchmarks" / "microbenchmark" / "dlmul" / "common"
CONTAINER_CASE_ROOT = CONTAINER_PROJECT_ROOT / "emulator" / "benchmarks" / "microbenchmark" / "dlmul" / "cases"
CONTAINER_CRT = CONTAINER_PROJECT_ROOT / "emulator" / "run" / "crt" / "crt_rv64.S"
CONTAINER_LINKER = CONTAINER_PROJECT_ROOT / "emulator" / "run" / "link" / "link_rv64.ld"

RESULT_COLUMNS = [
    "run_id",
    "created_at",
    "suite",
    "case_name",
    "variant_name",
    "sample_index",
    "target",
    "status",
    "failure",
    "failure_message",
    "kernel_cycles",
    "total_cycles",
    "wall_time_s",
    "sim_speed_khz",
    "params_json",
    "source_path",
    "elf_path",
    "objdump_path",
    "objdump_text",
    "container_log_path",
    "container_log_text",
    "run_detail_path",
    "run_detail_text",
    "trace_file",
    "command",
]


@dataclass(frozen=True)
class VariantSpec:
    name: str
    defines: dict[str, str]
    params: dict[str, Any]
    sample_count: int = 1


@dataclass(frozen=True)
class CaseSpec:
    suite: str
    case_name: str
    source_path: str
    variants: tuple[VariantSpec, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run dynamic LMUL assembly microbenchmarks on XiangShan and save results to SQLite."
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite output path")
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT, help="Artifact output root")
    parser.add_argument("--case", default="all", help="Case filter, or comma-separated list")
    parser.add_argument("--variant", default="all", help="Variant filter, or comma-separated list")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Simulation timeout in seconds")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel job count")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="run-sim target token")
    return parser.parse_args()


def fail(message: str, exit_code: int = 2) -> "NoReturn":
    print(message)
    raise SystemExit(exit_code)


def validate_positive_int(name: str, value: int) -> None:
    if value <= 0:
        fail(f"{name} must be a positive integer")


def resolve_timeout(timeout_s: int, target: str) -> int:
    if target.startswith("xiangshan") and timeout_s == LEGACY_TIMEOUT_S:
        return XIANSHAN_DEFAULT_TIMEOUT_S
    return timeout_s


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
        fail(f"Docker image not found: {image}")


def resolve_output_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (root / value).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_log_root(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (root / value).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_filter(value: str) -> set[str] | None:
    if not value or value == "all":
        return None
    entries = {entry.strip() for entry in value.split(",") if entry.strip()}
    return entries or None


def parse_run_sim_output(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Status:"):
            parsed["status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Exit code:"):
            parsed["exit_code"] = int(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("Wall time:"):
            parsed["wall_time_s"] = float(stripped.split(":", 1)[1].strip().removesuffix("s"))
        elif stripped.startswith("Kernel:"):
            parsed["kernel_cycles"] = int(stripped.split(":", 1)[1].strip().split()[0].replace(",", ""))
        elif stripped.startswith("Total sim:"):
            parsed["total_cycles"] = int(stripped.split(":", 1)[1].strip().split()[0].replace(",", ""))
        elif stripped.startswith("Sim speed:"):
            parsed["sim_speed_khz"] = float(stripped.split(":", 1)[1].strip().split()[0])
        elif stripped.startswith("Log file:"):
            parsed["run_detail_path"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Trace:"):
            parsed["trace_file"] = stripped.split(":", 1)[1].strip()
    return parsed


def map_container_output_path(path_text: str, host_output_dir: Path) -> Path:
    path = Path(path_text)
    try:
        relative = path.relative_to(CONTAINER_OUTPUT_ROOT)
    except ValueError:
        return path
    return host_output_dir / relative


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE microbench_results (
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            suite TEXT NOT NULL,
            case_name TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            sample_index INTEGER NOT NULL,
            target TEXT NOT NULL,
            status TEXT NOT NULL,
            failure TEXT NOT NULL,
            failure_message TEXT NOT NULL,
            kernel_cycles INTEGER,
            total_cycles INTEGER,
            wall_time_s REAL,
            sim_speed_khz REAL,
            params_json TEXT NOT NULL,
            source_path TEXT NOT NULL,
            elf_path TEXT NOT NULL,
            objdump_path TEXT NOT NULL,
            objdump_text TEXT NOT NULL,
            container_log_path TEXT NOT NULL,
            container_log_text TEXT NOT NULL,
            run_detail_path TEXT NOT NULL,
            run_detail_text TEXT NOT NULL,
            trace_file TEXT NOT NULL,
            command TEXT NOT NULL,
            PRIMARY KEY (case_name, variant_name, sample_index)
        )
        """
    )
    conn.commit()


def insert_row(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    values = [row.get(column) for column in RESULT_COLUMNS]
    placeholders = ", ".join("?" for _ in RESULT_COLUMNS)
    columns = ", ".join(RESULT_COLUMNS)
    conn.execute(
        f"INSERT OR REPLACE INTO microbench_results ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()


def make_manifest() -> tuple[CaseSpec, ...]:
    return (
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb1-switch",
            source_path="emulator/benchmarks/microbenchmark/dlmul/cases/mb1_switch.S",
            variants=(
                VariantSpec(
                    name="m1_to_m4",
                    defines={"SWITCH_FROM_LMUL": "m1", "SWITCH_TO_LMUL": "m4"},
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "m4", "first_avl": 64, "second_avl": 64, "outer_iters": 256},
                ),
                VariantSpec(
                    name="m4_to_m1",
                    defines={"SWITCH_FROM_LMUL": "m4", "SWITCH_TO_LMUL": "m1"},
                    params={"kind": "switch", "from_lmul": "m4", "to_lmul": "m1", "first_avl": 64, "second_avl": 64, "outer_iters": 256},
                ),
                VariantSpec(
                    name="m1_to_m8",
                    defines={"SWITCH_FROM_LMUL": "m1", "SWITCH_TO_LMUL": "m8"},
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "m8", "first_avl": 64, "second_avl": 64, "outer_iters": 256},
                ),
                VariantSpec(
                    name="m1_to_mf2",
                    defines={"SWITCH_FROM_LMUL": "m1", "SWITCH_TO_LMUL": "mf2"},
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "mf2", "first_avl": 64, "second_avl": 64, "outer_iters": 256},
                ),
                VariantSpec(
                    name="m1_reconfig",
                    defines={"SWITCH_FROM_LMUL": "m1", "SWITCH_TO_LMUL": "m1", "SWITCH_SECOND_AVL": "32"},
                    params={"kind": "same_lmul_reconfig", "from_lmul": "m1", "to_lmul": "m1", "first_avl": 64, "second_avl": 32, "outer_iters": 256},
                ),
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb2-memory-phase",
            source_path="emulator/benchmarks/microbenchmark/dlmul/cases/mb2_memory_phase.S",
            variants=tuple(
                VariantSpec(
                    name=lmul_name,
                    defines={"MEM_LMUL": lmul_name},
                    params={"kind": "memory_phase", "lmul": lmul_name, "total_elems": 256, "outer_iters": 64},
                )
                for lmul_name in ("m1", "m4", "m8")
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb3-fractional-rescue",
            source_path="emulator/benchmarks/microbenchmark/dlmul/cases/mb3_fractional_rescue.S",
            variants=tuple(
                VariantSpec(
                    name=f"{lmul_name}_k{temp_count}",
                    defines={"PRESSURE_LMUL": lmul_name, "TEMP_REG_COUNT": str(temp_count)},
                    params={"kind": "fractional_rescue", "lmul": lmul_name, "temp_reg_count": temp_count, "total_elems": 64, "outer_iters": 48},
                )
                for lmul_name in ("mf4", "mf2", "m1", "m2")
                for temp_count in (8,)
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb4-two-phase",
            source_path="emulator/benchmarks/microbenchmark/dlmul/cases/mb4_two_phase.S",
            variants=(
                VariantSpec(
                    name="fixed_m1",
                    defines={"PHASE1_LMUL": "m1", "PHASE2_LMUL": "m1"},
                    params={"kind": "two_phase", "phase1_lmul": "m1", "phase2_lmul": "m1", "mode": "fixed", "phase1_total_elems": 256, "phase2_total_elems": 64, "outer_iters": 48},
                ),
                VariantSpec(
                    name="fixed_m4",
                    defines={"PHASE1_LMUL": "m4", "PHASE2_LMUL": "m4"},
                    params={"kind": "two_phase", "phase1_lmul": "m4", "phase2_lmul": "m4", "mode": "fixed", "phase1_total_elems": 256, "phase2_total_elems": 64, "outer_iters": 48},
                ),
                VariantSpec(
                    name="fixed_m8",
                    defines={"PHASE1_LMUL": "m8", "PHASE2_LMUL": "m8"},
                    params={"kind": "two_phase", "phase1_lmul": "m8", "phase2_lmul": "m8", "mode": "fixed", "phase1_total_elems": 256, "phase2_total_elems": 64, "outer_iters": 48},
                ),
                VariantSpec(
                    name="m8_to_m1",
                    defines={"PHASE1_LMUL": "m8", "PHASE2_LMUL": "m1"},
                    params={"kind": "two_phase", "phase1_lmul": "m8", "phase2_lmul": "m1", "mode": "mixed", "phase1_total_elems": 256, "phase2_total_elems": 64, "outer_iters": 48},
                ),
                VariantSpec(
                    name="m4_to_mf2",
                    defines={"PHASE1_LMUL": "m4", "PHASE2_LMUL": "mf2"},
                    params={"kind": "two_phase", "phase1_lmul": "m4", "phase2_lmul": "mf2", "mode": "mixed", "phase1_total_elems": 256, "phase2_total_elems": 64, "outer_iters": 48},
                ),
            ),
        ),
    )


def iter_selected_jobs(
    manifest: tuple[CaseSpec, ...],
    case_filter: set[str] | None,
    variant_filter: set[str] | None,
) -> list[tuple[CaseSpec, VariantSpec, int]]:
    jobs: list[tuple[CaseSpec, VariantSpec, int]] = []
    for case in manifest:
        if case_filter is not None and case.case_name not in case_filter:
            continue
        for variant in case.variants:
            if variant_filter is not None and variant.name not in variant_filter:
                continue
            for sample_index in range(1, variant.sample_count + 1):
                jobs.append((case, variant, sample_index))
    return jobs


def build_define_args(defines: dict[str, str]) -> str:
    items = [f"-D{name}={value}" for name, value in sorted(defines.items())]
    return " ".join(shlex.quote(item) for item in items)


def build_inner_script(
    *,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    timeout_s: int,
    target: str,
) -> str:
    case_source = CONTAINER_PROJECT_ROOT / case.source_path
    elf_name = f"{case.case_name}_{variant.name}_s{sample_index:02d}.elf"
    objdump_name = f"{case.case_name}_{variant.name}_s{sample_index:02d}.objdump"
    elf_path = CONTAINER_OUTPUT_ROOT / "build" / elf_name
    objdump_path = CONTAINER_OUTPUT_ROOT / "build" / objdump_name
    define_args = build_define_args(variant.defines)

    lines = [
        "set -eu",
        'CLANG="$(command -v clang)"',
        'OBJDUMP="$(command -v llvm-objdump || command -v riscv64-unknown-elf-objdump)"',
        'if [ -z "$CLANG" ]; then echo "clang not found" >&2; exit 127; fi',
        'if [ -z "$OBJDUMP" ]; then echo "objdump not found" >&2; exit 127; fi',
        f"mkdir -p {shlex.quote(str(CONTAINER_OUTPUT_ROOT / 'build'))}",
        f"mkdir -p {shlex.quote(str(CONTAINER_OUTPUT_ROOT / 'logs'))}",
        (
            f'"$CLANG" --target=riscv64-unknown-elf -march=rv64gcv -mabi=lp64d '
            f'-mcmodel=medany -nostdlib -static -fuse-ld=lld '
            f'-I {shlex.quote(str(CONTAINER_COMMON_ROOT))} '
            f'{define_args} '
            f'{shlex.quote(str(CONTAINER_CRT))} '
            f'{shlex.quote(str(CONTAINER_COMMON_ROOT / "entry.S"))} '
            f'{shlex.quote(str(case_source))} '
            f'-Wl,-T,{shlex.quote(str(CONTAINER_LINKER))} '
            f'-o {shlex.quote(str(elf_path))}'
        ),
        f'"$OBJDUMP" -d {shlex.quote(str(elf_path))} > {shlex.quote(str(objdump_path))}',
        (
            f'cd {shlex.quote(str(CONTAINER_EMULATOR_ROOT))} && '
            f'python3 {shlex.quote(str(CONTAINER_RUN_SIM))} {shlex.quote(target)} '
            f'{shlex.quote(str(elf_path))} '
            f'--timeout={timeout_s} '
            f'--log-dir={shlex.quote(str(CONTAINER_OUTPUT_ROOT / "logs"))}'
        ),
    ]
    return "\n".join(lines)


def build_docker_command(
    *,
    root: Path,
    host_output_dir: Path,
    image: str,
    inner_script: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--platform",
        DEFAULT_PLATFORM,
        "-v",
        f"{root}:{CONTAINER_PROJECT_ROOT}:ro",
        "-v",
        f"{host_output_dir}:{CONTAINER_OUTPUT_ROOT}",
        "-v",
        f"{root / 'emulator' / 'run-sim.sh'}:{CONTAINER_RUN_SIM}:ro",
        "-v",
        f"{root / 'emulator' / 'sim-configs.yaml'}:{CONTAINER_SIM_CONFIG}:ro",
        image,
        "bash",
        "-lc",
        inner_script,
    ]


def make_output_dir(log_root: Path, run_id: str, case_name: str, variant_name: str, sample_index: int) -> Path:
    out_dir = log_root / run_id / case_name / variant_name / f"sample-{sample_index:02d}"
    out_dir.mkdir(parents=True, exist_ok=False)
    return out_dir


def make_base_row(
    *,
    run_id: str,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    target: str,
    source_path: str,
    command: str,
    container_log_path: str,
    params_json: str,
) -> dict[str, Any]:
    row = {column: "" for column in RESULT_COLUMNS}
    row.update(
        {
            "run_id": run_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "suite": case.suite,
            "case_name": case.case_name,
            "variant_name": variant.name,
            "sample_index": sample_index,
            "target": target,
            "status": "ERROR",
            "failure": "",
            "failure_message": "",
            "params_json": params_json,
            "source_path": source_path,
            "container_log_path": container_log_path,
            "command": command,
        }
    )
    return row


def run_job(
    *,
    root: Path,
    run_id: str,
    image: str,
    log_root: Path,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    timeout_s: int,
    target: str,
) -> dict[str, Any]:
    effective_timeout_s = resolve_timeout(timeout_s, target)
    params = dict(variant.params)
    params["sample_index"] = sample_index
    params["timeout_s"] = effective_timeout_s
    source_path = str((root / case.source_path).resolve())
    host_output_dir = make_output_dir(log_root, run_id, case.case_name, variant.name, sample_index)
    container_log_path = host_output_dir / "container.log"
    inner_script = build_inner_script(
        case=case,
        variant=variant,
        sample_index=sample_index,
        timeout_s=effective_timeout_s,
        target=target,
    )
    docker_cmd = build_docker_command(root=root, host_output_dir=host_output_dir, image=image, inner_script=inner_script)
    command = shlex.join(docker_cmd)
    row = make_base_row(
        run_id=run_id,
        case=case,
        variant=variant,
        sample_index=sample_index,
        target=target,
        source_path=source_path,
        command=command,
        container_log_path=str(container_log_path),
        params_json=json.dumps(params, sort_keys=True),
    )

    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=False)
    except Exception as exc:
        row["failure"] = "docker_exception"
        row["failure_message"] = str(exc)
        return row

    output_text = (result.stdout or "") + (result.stderr or "")
    container_log_path.write_text(output_text, encoding="utf-8")
    row["container_log_text"] = output_text

    elf_name = f"{case.case_name}_{variant.name}_s{sample_index:02d}.elf"
    objdump_name = f"{case.case_name}_{variant.name}_s{sample_index:02d}.objdump"
    elf_path = host_output_dir / "build" / elf_name
    objdump_path = host_output_dir / "build" / objdump_name
    row["elf_path"] = str(elf_path)
    row["objdump_path"] = str(objdump_path)
    if objdump_path.exists():
        row["objdump_text"] = objdump_path.read_text(encoding="utf-8")

    parsed = parse_run_sim_output(output_text)
    row["status"] = str(parsed.get("status", f"EXIT:{result.returncode}"))
    row["kernel_cycles"] = parsed.get("kernel_cycles")
    row["total_cycles"] = parsed.get("total_cycles")
    row["wall_time_s"] = parsed.get("wall_time_s")
    row["sim_speed_khz"] = parsed.get("sim_speed_khz")

    if "run_detail_path" in parsed:
        run_detail_path = map_container_output_path(str(parsed["run_detail_path"]), host_output_dir)
        row["run_detail_path"] = str(run_detail_path)
        if run_detail_path.exists():
            row["run_detail_text"] = run_detail_path.read_text(encoding="utf-8")
    if "trace_file" in parsed:
        trace_file = map_container_output_path(str(parsed["trace_file"]), host_output_dir)
        row["trace_file"] = str(trace_file)

    if result.returncode != 0:
        row["failure"] = "docker_failed"
        row["failure_message"] = f"docker exit code {result.returncode}"
        return row
    if not elf_path.exists():
        row["failure"] = "missing_elf"
        row["failure_message"] = "expected ELF was not generated"
        return row
    if not objdump_path.exists():
        row["failure"] = "missing_objdump"
        row["failure_message"] = "expected objdump was not generated"
        return row
    if row["kernel_cycles"] in ("", None):
        row["failure"] = "missing_kernel_cycles"
        row["failure_message"] = "run-sim output did not include kernel cycles"
        return row

    return row


def main() -> None:
    args = parse_args()
    validate_positive_int("timeout", args.timeout)
    validate_positive_int("concurrency", args.concurrency)

    root = repo_root()
    db_path = resolve_output_path(root, args.db_path)
    log_root = resolve_log_root(root, args.log_root)
    ensure_image_exists(args.image)

    manifest = make_manifest()
    selected_jobs = iter_selected_jobs(
        manifest,
        parse_filter(args.case),
        parse_filter(args.variant),
    )
    if not selected_jobs:
        fail("no microbench jobs matched the requested filters")

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    create_table(conn)

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"dlmul-microbench: jobs={len(selected_jobs)} target={args.target} db={db_path}")

    failures = 0
    completed = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_map = {
            executor.submit(
                run_job,
                root=root,
                run_id=run_id,
                image=args.image,
                log_root=log_root,
                case=case,
                variant=variant,
                sample_index=sample_index,
                timeout_s=args.timeout,
                target=args.target,
            ): (case.case_name, variant.name, sample_index)
            for case, variant, sample_index in selected_jobs
        }

        for future in as_completed(future_map):
            case_name, variant_name, sample_index = future_map[future]
            completed += 1
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    column: "" for column in RESULT_COLUMNS
                }
                row.update(
                    {
                        "run_id": run_id,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "suite": "dynamic_lmul",
                        "case_name": case_name,
                        "variant_name": variant_name,
                        "sample_index": sample_index,
                        "target": args.target,
                        "status": "ERROR",
                        "failure": "job_exception",
                        "failure_message": str(exc),
                        "params_json": "{}",
                    }
                )
            if row.get("failure"):
                failures += 1
            insert_row(conn, row)
            status_text = "fail" if row.get("failure") else str(row.get("status", "done")).lower()
            print(f"[{completed}/{len(selected_jobs)}] {case_name} {variant_name} s{sample_index:02d} {status_text}")

    conn.close()
    print(f"done: failures={failures} db={db_path}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
