#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import benchmark_sources
    import emulate
    import vplan_explain
except ModuleNotFoundError:
    from scripts import benchmark_sources, emulate, vplan_explain


DEFAULT_DB_DIR = "artifacts/emulate-results"
DEFAULT_CONCURRENCY = 5
DEFAULT_VFS_DB_DIR = "artifacts/vfs"
DEFAULT_VFS_DB = "artifacts/vfs.db"

TABLE_COLUMNS = [
    "run_id",
    "created_at",
    "stage",
    "failure",
    "failure_message",
    "bench",
    "use_vf",
    "benchmark",
    "image",
    "simulator_target",
    "len_1d",
    "lmul",
    "timeout_s",
    "effective_timeout_s",
    "docker_exit_code",
    "status",
    "exit_code",
    "wall_time_s",
    "kernel_cycles",
    "total_cycles",
    "sim_speed_khz",
    "artifact_dir",
    "container_log",
    "run_detail_path",
    "trace_file",
    "report_file",
    "docker_command",
    "source",
    "vplan_log_path",
    "vplan_log_text",
    "container_log_text",
    "run_detail",
    "opt_ll_text",
    "asm_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run emulate across all catalog workloads using precomputed VF candidates."
    )
    parser.add_argument("--image", default=emulate.DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--len", dest="len_1d", type=int, default=4096, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value")
    parser.add_argument("--timeout", type=int, default=120, help="Simulation timeout in seconds")
    parser.add_argument(
        "--log-root",
        default=emulate.DEFAULT_LOG_ROOT,
        help="Host output root for emulate artifacts",
    )
    parser.add_argument(
        "--vplan-log-root",
        default=vplan_explain.DEFAULT_OUTPUT_ROOT,
        help="Host output root for vplan-explain artifacts",
    )
    parser.add_argument("--arch", default="RVV", choices=["RVV", "MAC", "INTEL"], help="Target architecture")
    parser.add_argument("--vlen", type=int, default=128, help="RVV vector length in bits")
    parser.add_argument("--llvm-custom", default="", help="Optional host LLVM build/bin directory")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel emulate job count")
    parser.add_argument(
        "--db-dir",
        default=DEFAULT_DB_DIR,
        help="Directory for per-workload emulate-result-<workload_id>-<run_id>.sqlite files",
    )
    parser.add_argument(
        "--db-path",
        default="",
        help="Compatibility aggregate SQLite output path",
    )
    parser.add_argument(
        "--vfs-db-dir",
        default=DEFAULT_VFS_DB_DIR,
        help="Directory containing per-workload vfs-<workload_id>.sqlite files",
    )
    parser.add_argument(
        "--vfs-db",
        default=DEFAULT_VFS_DB,
        help="Compatibility aggregate VFS SQLite path",
    )
    parser.add_argument(
        "--catalog-dir",
        default="",
        help=f"Optional workload subdirectory under {benchmark_sources.RUN_SRC_ROOT}",
    )
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang")
    parser.add_argument("--extra-opt-flags", default="", help="Extra flags passed to opt")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    emulate.validate_positive_int("len", args.len_1d)
    emulate.validate_positive_int("lmul", args.lmul)
    emulate.validate_positive_int("timeout", args.timeout)
    emulate.validate_positive_int("concurrency", args.concurrency)
    if args.arch == "RVV" and args.vlen <= 0:
        emulate.fail("vlen must be a positive integer")


def discover_workloads(root: Path, catalog_dir: str = "") -> list[benchmark_sources.CatalogWorkload]:
    return benchmark_sources.discover_catalog_workloads(root, catalog_dir)


def discover_benches(root: Path, catalog_dir: str = "") -> list[str]:
    return benchmark_sources.discover_catalog_benches(root, catalog_dir)


def resolve_db_dir(root: Path, db_dir: str) -> Path:
    path = Path(db_dir)
    if not path.is_absolute():
        path = (root / db_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_existing_dir(root: Path, path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (root / path_text).resolve()
    return path


def normalize_result_name_component(value: str, fallback: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", value.lower())
    return "-".join(tokens) if tokens else fallback


def result_scope_label(catalog_dir: str, default_label: str) -> str:
    if not catalog_dir.strip():
        return default_label
    return normalize_result_name_component(catalog_dir, fallback=default_label)


def aggregate_db_filename(
    *,
    prefix: str,
    arch: str,
    bench_label: str,
    run_id: str,
) -> str:
    return (
        f"{prefix}-"
        f"{normalize_result_name_component(arch, fallback='unknown')}-"
        f"{normalize_result_name_component(bench_label, fallback='all')}-"
        f"{run_id}.sqlite"
    )


def default_aggregate_db_path(
    root: Path,
    *,
    prefix: str,
    arch: str,
    bench_label: str,
    run_id: str,
) -> Path:
    path = (root / "artifacts" / aggregate_db_filename(
        prefix=prefix,
        arch=arch,
        bench_label=bench_label,
        run_id=run_id,
    )).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_db_path(
    root: Path,
    db_path: str,
    run_id: str,
    *,
    prefix: str,
    arch: str,
    bench_label: str,
) -> Path:
    if db_path:
        path = Path(db_path)
        if not path.is_absolute():
            path = (root / db_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return default_aggregate_db_path(
        root,
        prefix=prefix,
        arch=arch,
        bench_label=bench_label,
        run_id=run_id,
    )


def resolve_input_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (root / value).resolve()
    if not path.exists():
        emulate.fail(f"input file not found: {path}")
    return path


def workload_result_db_path(db_dir: Path, workload_id: str, run_id: str) -> Path:
    return db_dir / f"emulate-result-{workload_id}-{run_id}.sqlite"


def workload_vfs_db_path(vfs_db_dir: Path, workload_id: str) -> Path:
    return vfs_db_dir / f"vfs-{workload_id}.sqlite"


def load_vfs_data(db_path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            bench,
            use_vf,
            raw_vf,
            cost,
            compare,
            plan_index,
            selected,
            failure,
            failure_message,
            source,
            vplan_log_path,
            vplan_log_text
        FROM vfs
        ORDER BY bench, use_vf
        """
    ).fetchall()
    conn.close()

    candidates_by_bench: dict[str, list[dict[str, Any]]] = {}
    failures_by_bench: dict[str, dict[str, Any]] = {}
    for row in rows:
        bench = str(row["bench"] or "")
        if not bench:
            continue
        failure = str(row["failure"] or "")
        record = {
            "bench": bench,
            "use_vf": str(row["use_vf"] or ""),
            "raw_vf": str(row["raw_vf"] or ""),
            "cost": str(row["cost"] or ""),
            "compare": str(row["compare"] or ""),
            "plan_index": row["plan_index"],
            "selected": bool(int(row["selected"] or 0)),
            "failure": failure,
            "failure_message": str(row["failure_message"] or ""),
            "source": str(row["source"] or ""),
            "vplan_log_path": str(row["vplan_log_path"] or ""),
            "vplan_log_text": str(row["vplan_log_text"] or ""),
        }
        if failure:
            failures_by_bench[bench] = record
            continue
        candidates_by_bench.setdefault(bench, []).append(record)
    return candidates_by_bench, failures_by_bench


def load_workload_vfs_records(
    *,
    workload_id: str,
    vfs_db_dir: Path | None,
    aggregate_vfs: tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if vfs_db_dir is not None:
        db_path = workload_vfs_db_path(vfs_db_dir, workload_id)
        if not db_path.exists():
            return [], {
                "bench": workload_id,
                "failure": "missing_vfs_db",
                "failure_message": f"workload VF DB missing: {db_path}",
                "source": "",
                "vplan_log_path": "",
                "vplan_log_text": "",
            }
        candidates_by_bench, failures_by_bench = load_vfs_data(db_path)
        return candidates_by_bench.get(workload_id, []), failures_by_bench.get(workload_id)

    if aggregate_vfs is None:
        return [], {
            "bench": workload_id,
            "failure": "missing_vfs_db",
            "failure_message": "no VFS input was provided",
            "source": "",
            "vplan_log_path": "",
            "vplan_log_text": "",
        }

    candidates_by_bench, failures_by_bench = aggregate_vfs
    if workload_id in failures_by_bench:
        return [], failures_by_bench[workload_id]
    if workload_id not in candidates_by_bench:
        return [], {
            "bench": workload_id,
            "failure": "missing_vfs_entry",
            "failure_message": "workload missing from aggregate vfs DB",
            "source": "",
            "vplan_log_path": "",
            "vplan_log_text": "",
        }
    return candidates_by_bench[workload_id], None


def make_vplan_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": record.get("source", ""),
        "vplan_log": record.get("vplan_log_path", ""),
        "vplan_log_text": record.get("vplan_log_text", ""),
        "container_log_text": "",
    }


def make_default_vplan_result() -> dict[str, Any]:
    return {
        "source": "",
        "vplan_log": "",
        "vplan_log_text": "",
        "container_log_text": "",
    }


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS emulate_results (
            run_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            stage TEXT NOT NULL,
            failure TEXT NOT NULL,
            failure_message TEXT NOT NULL,
            bench TEXT NOT NULL,
            use_vf TEXT NOT NULL,
            benchmark TEXT,
            image TEXT,
            simulator_target TEXT,
            len_1d INTEGER,
            lmul INTEGER,
            timeout_s INTEGER,
            effective_timeout_s INTEGER,
            docker_exit_code INTEGER,
            status TEXT,
            exit_code INTEGER,
            wall_time_s REAL,
            kernel_cycles INTEGER,
            total_cycles INTEGER,
            sim_speed_khz REAL,
            artifact_dir TEXT,
            container_log TEXT,
            run_detail_path TEXT,
            trace_file TEXT,
            report_file TEXT,
            docker_command TEXT,
            source TEXT,
            vplan_log_path TEXT,
            vplan_log_text TEXT,
            container_log_text TEXT,
            run_detail TEXT,
            opt_ll_text VARCHAR,
            asm_text VARCHAR,
            PRIMARY KEY (stage, bench, use_vf)
        )
        """
    )
    conn.commit()


def make_empty_row(run_id: str, bench: str, use_vf: str) -> dict[str, Any]:
    row = {column: None for column in TABLE_COLUMNS}
    row["run_id"] = run_id
    row["created_at"] = datetime.now().isoformat(timespec="seconds")
    row["stage"] = ""
    row["failure"] = ""
    row["failure_message"] = ""
    row["bench"] = bench
    row["use_vf"] = use_vf
    for column in emulate.BUILD_ARTIFACT_SUFFIXES:
        row[column] = ""
    return row


def insert_row(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    values = [row.get(column) for column in TABLE_COLUMNS]
    placeholders = ", ".join("?" for _ in TABLE_COLUMNS)
    columns = ", ".join(TABLE_COLUMNS)
    conn.execute(
        f"INSERT OR REPLACE INTO emulate_results ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()


def insert_row_to_db(db_path: Path, row: dict[str, Any]) -> None:
    conn = sqlite3.connect(db_path)
    create_table(conn)
    insert_row(conn, row)
    conn.close()


def make_vplan_failure_row(
    *,
    run_id: str,
    bench: str,
    args: argparse.Namespace,
    failure: str,
    message: str,
    vplan_result: dict[str, Any],
) -> dict[str, Any]:
    row = make_empty_row(run_id, bench, "")
    row.update(
        {
            "stage": "vplan",
            "failure": failure,
            "failure_message": message,
            "benchmark": bench,
            "image": getattr(args, "image", ""),
            "len_1d": args.len_1d,
            "lmul": args.lmul,
            "timeout_s": getattr(args, "timeout", None),
            "status": "SKIP",
            "source": vplan_result.get("source"),
            "vplan_log_path": vplan_result.get("vplan_log"),
            "vplan_log_text": vplan_result.get("vplan_log_text") or vplan_result.get("container_log_text"),
            "container_log_text": vplan_result.get("container_log_text"),
        }
    )
    return row


def make_emulate_row(
    *,
    run_id: str,
    bench: str,
    use_vf: str,
    args: argparse.Namespace,
    vplan_result: dict[str, Any],
    emulate_result: dict[str, Any] | None,
    failure: str = "",
    failure_message: str = "",
) -> dict[str, Any]:
    row = make_empty_row(run_id, bench, use_vf)
    row.update(
        {
            "stage": "emulate",
            "failure": failure,
            "failure_message": failure_message,
            "benchmark": bench,
            "image": args.image,
            "len_1d": args.len_1d,
            "lmul": args.lmul,
            "timeout_s": args.timeout,
            "source": vplan_result.get("source") or "",
            "vplan_log_path": vplan_result.get("vplan_log"),
            "vplan_log_text": vplan_result.get("vplan_log_text") or vplan_result.get("container_log_text"),
        }
    )
    if emulate_result is None:
        row["status"] = "ERROR"
        return row

    summary = emulate_result["summary"]
    row.update(summary)
    row["bench"] = bench
    row["use_vf"] = use_vf
    row["container_log_text"] = emulate_result.get("container_log_text", "")
    row["run_detail"] = emulate_result.get("run_detail", "")
    for column in emulate.BUILD_ARTIFACT_SUFFIXES:
        row[column] = str(emulate_result.get(column, "") or "")
    return row


def run_emulate_job(
    *,
    bench: str,
    use_vf: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return emulate.run_emulate(
        bench=bench,
        image=args.image,
        len_1d=args.len_1d,
        lmul=args.lmul,
        use_vf=use_vf,
        timeout_s=args.timeout,
        log_root=args.log_root,
        ensure_image=False,
        extra_cflags=args.extra_cflags,
        extra_opt_flags=args.extra_opt_flags,
    )


def find_missing_artifacts(emulate_result: dict[str, Any], use_vf: str) -> list[str]:
    del use_vf
    return [column for column in emulate.BUILD_ARTIFACT_SUFFIXES if not emulate_result.get(column)]


def export_aggregate_db(workload_dbs: list[Path], aggregate_db_path: Path) -> None:
    if aggregate_db_path.exists():
        aggregate_db_path.unlink()

    conn = sqlite3.connect(aggregate_db_path)
    create_table(conn)
    placeholders = ", ".join("?" for _ in TABLE_COLUMNS)
    columns = ", ".join(TABLE_COLUMNS)

    for workload_db in workload_dbs:
        source_conn = sqlite3.connect(workload_db)
        rows = source_conn.execute(
            f"SELECT {columns} FROM emulate_results ORDER BY stage, bench, use_vf"
        ).fetchall()
        source_conn.close()
        if rows:
            conn.executemany(
                f"INSERT INTO emulate_results ({columns}) VALUES ({placeholders})",
                rows,
            )
            conn.commit()

    conn.close()


def main() -> None:
    args = parse_args()
    validate_args(args)

    root = emulate.repo_root()
    run_id = datetime.now().strftime("%Y%m%d%H%M")
    db_dir = resolve_db_dir(root, args.db_dir)
    aggregate_db_path = resolve_db_path(
        root,
        args.db_path,
        run_id,
        prefix="emulate-result",
        arch=args.arch,
        bench_label=result_scope_label(args.catalog_dir, default_label="all"),
    )
    benches = discover_benches(root, args.catalog_dir)

    emulate.ensure_image_exists(args.image)

    vfs_db_dir: Path | None = None
    aggregate_vfs: tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]] | None = None
    if args.vfs_db_dir:
        candidate_vfs_dir = resolve_existing_dir(root, args.vfs_db_dir)
        if candidate_vfs_dir.exists():
            vfs_db_dir = candidate_vfs_dir
    if vfs_db_dir is None and args.vfs_db:
        aggregate_db = resolve_existing_dir(root, args.vfs_db)
        if aggregate_db.exists():
            aggregate_vfs = load_vfs_data(aggregate_db)

    print(
        f"emulate-all: workloads={len(benches)} catalog_dir={args.catalog_dir or '.'} "
        f"parallel={args.concurrency} db_dir={db_dir.name} aggregate={aggregate_db_path.name}"
    )

    scheduled: list[tuple[str, str, dict[str, Any], Path]] = []
    workload_dbs: list[Path] = []

    for index, bench in enumerate(benches, start=1):
        workload_db = workload_result_db_path(db_dir, bench, run_id)
        if workload_db.exists():
            workload_db.unlink()
        workload_dbs.append(workload_db)

        candidate_records, failure_record = load_workload_vfs_records(
            workload_id=bench,
            vfs_db_dir=vfs_db_dir,
            aggregate_vfs=aggregate_vfs,
        )

        if failure_record is not None:
            insert_row_to_db(
                workload_db,
                make_vplan_failure_row(
                    run_id=run_id,
                    bench=bench,
                    args=args,
                    failure=str(failure_record["failure"] or "vplan_failed"),
                    message=str(failure_record["failure_message"] or "vplan-explain failed"),
                    vplan_result=make_vplan_result(failure_record),
                ),
            )
            print(f"[vplan {index}/{len(benches)}] {bench} {failure_record['failure']}")
        else:
            print(f"[vplan {index}/{len(benches)}] {bench} vf={len(candidate_records)}")

        for candidate_record in candidate_records:
            scheduled.append(
                (bench, str(candidate_record["use_vf"]), make_vplan_result(candidate_record), workload_db)
            )
        scheduled.append((bench, "", make_default_vplan_result(), workload_db))

    print(f"emulate-jobs: {len(scheduled)}")

    completed = 0
    total_jobs = len(scheduled)
    emulate_failures = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_map = {
            executor.submit(
                run_emulate_job,
                bench=bench,
                use_vf=use_vf,
                args=args,
            ): (bench, use_vf, vplan_result, workload_db)
            for bench, use_vf, vplan_result, workload_db in scheduled
        }

        for future in as_completed(future_map):
            bench, use_vf, vplan_result, workload_db = future_map[future]
            completed += 1
            try:
                emulate_result = future.result()
            except Exception as exc:
                emulate_failures += 1
                row = make_emulate_row(
                    run_id=run_id,
                    bench=bench,
                    use_vf=use_vf,
                    args=args,
                    vplan_result=vplan_result,
                    emulate_result=None,
                    failure="emulate_exception",
                    failure_message=str(exc),
                )
                insert_row_to_db(workload_db, row)
                print(f"[emu {completed}/{total_jobs}] {bench} {use_vf} fail")
                continue

            failure = ""
            failure_message = ""
            if emulate_result["failed"]:
                emulate_failures += 1
                failure = "emulate_failed"
                failure_message = str(emulate_result["summary"].get("status", "emulate failed"))
            else:
                missing_artifacts = find_missing_artifacts(emulate_result, use_vf)
                if missing_artifacts:
                    emulate_failures += 1
                    failure = "artifact_capture_failed"
                    failure_message = f"missing artifacts: {', '.join(missing_artifacts)}"

            row = make_emulate_row(
                run_id=run_id,
                bench=bench,
                use_vf=use_vf,
                args=args,
                vplan_result=vplan_result,
                emulate_result=emulate_result,
                failure=failure,
                failure_message=failure_message,
            )
            insert_row_to_db(workload_db, row)
            status_text = "fail" if failure else str(row.get("status", "done")).lower()
            print(f"[emu {completed}/{total_jobs}] {bench} {use_vf} {status_text}")

    export_aggregate_db(workload_dbs, aggregate_db_path)
    print(f"done: emulate_failures={emulate_failures} aggregate={aggregate_db_path}")

    if emulate_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
