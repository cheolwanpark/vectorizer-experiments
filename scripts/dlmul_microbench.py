#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

try:
    import emulate
except ModuleNotFoundError:
    from scripts import emulate


DEFAULT_DB_PATH = "artifacts/microbench.sqlite"
DEFAULT_LOG_ROOT = "artifacts/microbench"
DEFAULT_CONCURRENCY = 1
DEFAULT_TIMEOUT = 120
DEFAULT_LEN_1D = 256
DEFAULT_LMUL = 1
CATALOG_ROOT = Path("emulator") / "run" / "src" / "microbench" / "dlmul"

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
    "artifact_dir",
    "container_log_path",
    "container_log_text",
    "run_detail_path",
    "run_detail_text",
    "trace_file",
    "opt_ll_text",
    "asm_text",
    "asm_check_status",
    "asm_check_message",
    "asm_expectation_json",
    "command",
]


@dataclass(frozen=True)
class VariantSpec:
    name: str
    defines: tuple[str, ...]
    params: dict[str, Any]
    asm_patterns: tuple[str, ...]
    sample_count: int = 1


@dataclass(frozen=True)
class CaseSpec:
    suite: str
    case_name: str
    source_path: str
    variants: tuple[VariantSpec, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run C-based dynamic LMUL microbenchmarks through emulate.py and save results to SQLite."
    )
    parser.add_argument("--image", default=emulate.DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite output path")
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT, help="Artifact output root")
    parser.add_argument("--case", default="all", help="Case filter, or comma-separated list")
    parser.add_argument("--variant", default="all", help="Variant filter, or comma-separated list")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Simulation timeout in seconds")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel job count")
    parser.add_argument("--target", default=emulate.SIM_TARGET, help="Reserved target token; only XiangShan is supported")
    return parser.parse_args()


def fail(message: str, exit_code: int = 2) -> NoReturn:
    print(message)
    raise SystemExit(exit_code)


def validate_positive_int(name: str, value: int) -> None:
    if value <= 0:
        fail(f"{name} must be a positive integer")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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
            artifact_dir TEXT NOT NULL,
            container_log_path TEXT NOT NULL,
            container_log_text TEXT NOT NULL,
            run_detail_path TEXT NOT NULL,
            run_detail_text TEXT NOT NULL,
            trace_file TEXT NOT NULL,
            opt_ll_text TEXT NOT NULL,
            asm_text TEXT NOT NULL,
            asm_check_status TEXT NOT NULL,
            asm_check_message TEXT NOT NULL,
            asm_expectation_json TEXT NOT NULL,
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


def ordered_patterns_match(text: str, patterns: tuple[str, ...]) -> tuple[bool, str]:
    if not patterns:
        return True, "no asm expectations configured"
    position = 0
    for index, pattern in enumerate(patterns, start=1):
        match = re.search(pattern, text[position:], re.MULTILINE)
        if match is None:
            return False, f"missing pattern {index}/{len(patterns)}: {pattern}"
        position += match.end()
    return True, "matched expected asm pattern order"


def build_extra_cflags(variant: VariantSpec) -> str:
    flags = ["-fno-vectorize", "-fno-slp-vectorize"]
    flags.extend(f"-D{define}" for define in variant.defines)
    return " ".join(flags)


def benchmark_id(case: CaseSpec, variant: VariantSpec) -> str:
    return f"dlmul_{case.case_name.replace('-', '_')}__{variant.name}"


def make_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT
    return (
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb1-switch",
            source_path=str(root / "mb1_switch.c"),
            variants=(
                VariantSpec(
                    name="m1_to_m4",
                    defines=("MB1_FROM_VARIANT=1", "MB1_TO_VARIANT=4", "MB1_FIRST_AVL=64", "MB1_SECOND_AVL=64", "MB1_OUTER_ITERS=256"),
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "m4", "first_avl": 64, "second_avl": 64, "outer_iters": 256, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b", r"vsetvli.*e32,\s*m4\b"),
                ),
                VariantSpec(
                    name="m4_to_m1",
                    defines=("MB1_FROM_VARIANT=4", "MB1_TO_VARIANT=1", "MB1_FIRST_AVL=64", "MB1_SECOND_AVL=64", "MB1_OUTER_ITERS=256"),
                    params={"kind": "switch", "from_lmul": "m4", "to_lmul": "m1", "first_avl": 64, "second_avl": 64, "outer_iters": 256, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m4\b", r"vsetvli.*e32,\s*m1\b"),
                ),
                VariantSpec(
                    name="m1_to_m8",
                    defines=("MB1_FROM_VARIANT=1", "MB1_TO_VARIANT=8", "MB1_FIRST_AVL=64", "MB1_SECOND_AVL=64", "MB1_OUTER_ITERS=256"),
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "m8", "first_avl": 64, "second_avl": 64, "outer_iters": 256, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b", r"vsetvli.*e32,\s*m8\b"),
                ),
                VariantSpec(
                    name="m1_to_mf2",
                    defines=("MB1_FROM_VARIANT=1", "MB1_TO_VARIANT=102", "MB1_FIRST_AVL=64", "MB1_SECOND_AVL=64", "MB1_OUTER_ITERS=256"),
                    params={"kind": "switch", "from_lmul": "m1", "to_lmul": "mf2", "first_avl": 64, "second_avl": 64, "outer_iters": 256, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b", r"vsetvli.*e32,\s*mf2\b"),
                ),
                VariantSpec(
                    name="m1_reconfig",
                    defines=("MB1_FROM_VARIANT=1", "MB1_TO_VARIANT=1", "MB1_FIRST_AVL=64", "MB1_SECOND_AVL=32", "MB1_OUTER_ITERS=256"),
                    params={"kind": "same_lmul_reconfig", "from_lmul": "m1", "to_lmul": "m1", "first_avl": 64, "second_avl": 32, "outer_iters": 256, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b", r"vsetvli.*e32,\s*m1\b"),
                ),
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb2-memory-phase",
            source_path=str(root / "mb2_memory_phase.c"),
            variants=(
                VariantSpec(
                    name="m1",
                    defines=("MB2_VARIANT=1", "MB2_TOTAL_ELEMS=256", "MB2_OUTER_ITERS=64"),
                    params={"kind": "memory_phase", "lmul": "m1", "total_elems": 256, "outer_iters": 64, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b",),
                ),
                VariantSpec(
                    name="m4",
                    defines=("MB2_VARIANT=4", "MB2_TOTAL_ELEMS=256", "MB2_OUTER_ITERS=64"),
                    params={"kind": "memory_phase", "lmul": "m4", "total_elems": 256, "outer_iters": 64, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m4\b",),
                ),
                VariantSpec(
                    name="m8",
                    defines=("MB2_VARIANT=8", "MB2_TOTAL_ELEMS=256", "MB2_OUTER_ITERS=64"),
                    params={"kind": "memory_phase", "lmul": "m8", "total_elems": 256, "outer_iters": 64, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m8\b",),
                ),
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb3-fractional-rescue",
            source_path=str(root / "mb3_fractional_rescue.c"),
            variants=(
                VariantSpec(
                    name="mf4_k8",
                    defines=("MB3_VARIANT=104", "MB3_TEMP_COUNT=8", "MB3_TOTAL_ELEMS=64", "MB3_OUTER_ITERS=48"),
                    params={"kind": "fractional_rescue", "lmul": "mf4", "temp_reg_count": 8, "total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*mf4\b",),
                ),
                VariantSpec(
                    name="mf2_k8",
                    defines=("MB3_VARIANT=102", "MB3_TEMP_COUNT=8", "MB3_TOTAL_ELEMS=64", "MB3_OUTER_ITERS=48"),
                    params={"kind": "fractional_rescue", "lmul": "mf2", "temp_reg_count": 8, "total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*mf2\b",),
                ),
                VariantSpec(
                    name="m1_k8",
                    defines=("MB3_VARIANT=1", "MB3_TEMP_COUNT=8", "MB3_TOTAL_ELEMS=64", "MB3_OUTER_ITERS=48"),
                    params={"kind": "fractional_rescue", "lmul": "m1", "temp_reg_count": 8, "total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b",),
                ),
                VariantSpec(
                    name="m2_k8",
                    defines=("MB3_VARIANT=2", "MB3_TEMP_COUNT=8", "MB3_TOTAL_ELEMS=64", "MB3_OUTER_ITERS=48"),
                    params={"kind": "fractional_rescue", "lmul": "m2", "temp_reg_count": 8, "total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m2\b",),
                ),
            ),
        ),
        CaseSpec(
            suite="dynamic_lmul",
            case_name="mb4-two-phase",
            source_path=str(root / "mb4_two_phase.c"),
            variants=(
                VariantSpec(
                    name="fixed_m1",
                    defines=("MB4_PHASE1_VARIANT=1", "MB4_PHASE2_VARIANT=1", "MB4_PHASE1_TOTAL_ELEMS=128", "MB4_PHASE2_TOTAL_ELEMS=64", "MB4_OUTER_ITERS=48"),
                    params={"kind": "two_phase", "phase1_lmul": "m1", "phase2_lmul": "m1", "phase1_total_elems": 128, "phase2_total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m1\b",),
                ),
                VariantSpec(
                    name="fixed_m4",
                    defines=("MB4_PHASE1_VARIANT=4", "MB4_PHASE2_VARIANT=4", "MB4_PHASE1_TOTAL_ELEMS=128", "MB4_PHASE2_TOTAL_ELEMS=64", "MB4_OUTER_ITERS=48"),
                    params={"kind": "two_phase", "phase1_lmul": "m4", "phase2_lmul": "m4", "phase1_total_elems": 128, "phase2_total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m4\b",),
                ),
                VariantSpec(
                    name="fixed_m8",
                    defines=("MB4_PHASE1_VARIANT=8", "MB4_PHASE2_VARIANT=8", "MB4_PHASE1_TOTAL_ELEMS=128", "MB4_PHASE2_TOTAL_ELEMS=64", "MB4_OUTER_ITERS=48"),
                    params={"kind": "two_phase", "phase1_lmul": "m8", "phase2_lmul": "m8", "phase1_total_elems": 128, "phase2_total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m8\b",),
                ),
                VariantSpec(
                    name="m8_to_m1",
                    defines=("MB4_PHASE1_VARIANT=8", "MB4_PHASE2_VARIANT=1", "MB4_PHASE1_TOTAL_ELEMS=128", "MB4_PHASE2_TOTAL_ELEMS=64", "MB4_OUTER_ITERS=48"),
                    params={"kind": "two_phase", "phase1_lmul": "m8", "phase2_lmul": "m1", "phase1_total_elems": 128, "phase2_total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m8\b", r"vsetvli.*e32,\s*m1\b", r"vsetvli.*e32,\s*m8\b"),
                ),
                VariantSpec(
                    name="m4_to_mf2",
                    defines=("MB4_PHASE1_VARIANT=4", "MB4_PHASE2_VARIANT=102", "MB4_PHASE1_TOTAL_ELEMS=128", "MB4_PHASE2_TOTAL_ELEMS=64", "MB4_OUTER_ITERS=48"),
                    params={"kind": "two_phase", "phase1_lmul": "m4", "phase2_lmul": "mf2", "phase1_total_elems": 128, "phase2_total_elems": 64, "outer_iters": 48, "len_1d": 256},
                    asm_patterns=(r"vsetvli.*e32,\s*m4\b", r"vsetvli.*e32,\s*mf2\b", r"vsetvli.*e32,\s*m4\b"),
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


def make_row_from_emulate_result(
    *,
    run_id: str,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    summary = result["summary"]
    asm_text = str(result.get("asm_text", "") or "")
    expectations_json = json.dumps(list(variant.asm_patterns))

    if result.get("failed"):
        asm_check_status = "SKIP"
        asm_check_message = "emulate run failed before asm validation"
    elif not asm_text:
        asm_check_status = "WARN"
        asm_check_message = "asm_text is empty"
    else:
        matched, message = ordered_patterns_match(asm_text, variant.asm_patterns)
        asm_check_status = "PASS" if matched else "WARN"
        asm_check_message = message

    return {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "suite": case.suite,
        "case_name": case.case_name,
        "variant_name": variant.name,
        "sample_index": sample_index,
        "target": str(summary.get("simulator_target", "")),
        "status": str(summary.get("status", "")),
        "failure": "emulate_failed" if result.get("failed") else "",
        "failure_message": str(summary.get("status", "")) if result.get("failed") else "",
        "kernel_cycles": summary.get("kernel_cycles"),
        "total_cycles": summary.get("total_cycles"),
        "wall_time_s": summary.get("wall_time_s"),
        "sim_speed_khz": summary.get("sim_speed_khz"),
        "params_json": json.dumps(variant.params, sort_keys=True),
        "source_path": str(summary.get("source", "")),
        "artifact_dir": str(summary.get("artifact_dir", "")),
        "container_log_path": str(summary.get("container_log", "")),
        "container_log_text": str(result.get("container_log_text", "") or ""),
        "run_detail_path": str(summary.get("run_detail_path", "") or ""),
        "run_detail_text": str(result.get("run_detail", "") or ""),
        "trace_file": str(summary.get("trace_file", "") or ""),
        "opt_ll_text": str(result.get("opt_ll_text", "") or ""),
        "asm_text": asm_text,
        "asm_check_status": asm_check_status,
        "asm_check_message": asm_check_message,
        "asm_expectation_json": expectations_json,
        "command": str(summary.get("docker_command", "")),
    }


def make_exception_row(
    *,
    run_id: str,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    target: str,
    exc: Exception,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "suite": case.suite,
        "case_name": case.case_name,
        "variant_name": variant.name,
        "sample_index": sample_index,
        "target": target,
        "status": "ERROR",
        "failure": "job_exception",
        "failure_message": str(exc),
        "kernel_cycles": None,
        "total_cycles": None,
        "wall_time_s": None,
        "sim_speed_khz": None,
        "params_json": json.dumps(variant.params, sort_keys=True),
        "source_path": "",
        "artifact_dir": "",
        "container_log_path": "",
        "container_log_text": "",
        "run_detail_path": "",
        "run_detail_text": "",
        "trace_file": "",
        "opt_ll_text": "",
        "asm_text": "",
        "asm_check_status": "SKIP",
        "asm_check_message": "job exception before asm validation",
        "asm_expectation_json": json.dumps(list(variant.asm_patterns)),
        "command": "",
    }


def run_job(
    *,
    case: CaseSpec,
    variant: VariantSpec,
    sample_index: int,
    image: str,
    log_root: str,
    timeout_s: int,
) -> dict[str, Any]:
    bench = benchmark_id(case, variant)
    source_path = case.source_path
    return emulate.run_emulate_source(
        benchmark=bench,
        source=source_path,
        image=image,
        len_1d=int(variant.params.get("len_1d", DEFAULT_LEN_1D)),
        lmul=int(variant.params.get("compiler_lmul", DEFAULT_LMUL)),
        use_vf="",
        timeout_s=timeout_s,
        log_root=log_root,
        ensure_image=False,
        extra_cflags=build_extra_cflags(variant),
        extra_opt_flags="",
    )


def main() -> None:
    args = parse_args()
    validate_positive_int("timeout", args.timeout)
    validate_positive_int("concurrency", args.concurrency)
    if args.target != emulate.SIM_TARGET:
        fail(f"dlmul-microbench currently supports only {emulate.SIM_TARGET}")

    root = repo_root()
    db_path = resolve_output_path(root, args.db_path)
    log_root = resolve_log_root(root, args.log_root)
    emulate.ensure_image_exists(args.image)

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
                case=case,
                variant=variant,
                sample_index=sample_index,
                image=args.image,
                log_root=str(log_root),
                timeout_s=args.timeout,
            ): (case, variant, sample_index)
            for case, variant, sample_index in selected_jobs
        }

        for future in as_completed(future_map):
            case, variant, sample_index = future_map[future]
            completed += 1
            try:
                result = future.result()
                row = make_row_from_emulate_result(
                    run_id=run_id,
                    case=case,
                    variant=variant,
                    sample_index=sample_index,
                    result=result,
                )
            except Exception as exc:
                row = make_exception_row(
                    run_id=run_id,
                    case=case,
                    variant=variant,
                    sample_index=sample_index,
                    target=args.target,
                    exc=exc,
                )
            if row["failure"]:
                failures += 1
            insert_row(conn, row)
            status_text = "fail" if row["failure"] else str(row["status"]).lower()
            if row["asm_check_status"] == "WARN" and not row["failure"]:
                status_text = "warn"
            print(
                f"[{completed}/{len(selected_jobs)}] "
                f"{case.case_name} {variant.name} s{sample_index:02d} {status_text}"
            )

    conn.close()
    print(f"done: failures={failures} db={db_path}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
