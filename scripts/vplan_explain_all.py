#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    import benchmark_sources
    import emulate
    import emulate_all
    import vplan_explain
except ModuleNotFoundError:
    from scripts import benchmark_sources, emulate, emulate_all, vplan_explain


DEFAULT_DB_DIR = "artifacts/vfs"
DEFAULT_COMPAT_DB_PATH = "artifacts/vfs.db"
VFS_COLUMNS = [
    "bench",
    "use_vf",
    "raw_vf",
    "cost",
    "compare",
    "plan_index",
    "selected",
    "failure",
    "failure_message",
    "source",
    "vplan_log_path",
    "vplan_log_text",
    "created_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run vplan-explain across all catalog workloads and save VF candidates to SQLite."
    )
    parser.add_argument("--image", default=vplan_explain.DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--platform", default=vplan_explain.DEFAULT_PLATFORM, help="Docker platform")
    parser.add_argument("--arch", default="RVV", choices=["RVV", "MAC", "INTEL"], help="Target architecture")
    parser.add_argument("--x86-march", default=vplan_explain.llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH, help="x86 -march value (for ARCH=INTEL)")
    parser.add_argument("--len", dest="len_1d", type=int, default=4096, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value")
    parser.add_argument("--vlen", type=int, default=128, help="RVV vector length in bits")
    parser.add_argument("--llvm-custom", default="", help="Optional host LLVM build/bin directory")
    parser.add_argument(
        "--output-root",
        default=vplan_explain.DEFAULT_OUTPUT_ROOT,
        help="Host output root for vplan-explain artifacts",
    )
    parser.add_argument(
        "--db-dir",
        default=DEFAULT_DB_DIR,
        help="Directory for per-workload vfs-<workload_id>.sqlite files",
    )
    parser.add_argument(
        "--db-path",
        default="",
        help="Optional aggregate SQLite output path",
    )
    parser.add_argument(
        "--compat-db-path",
        default=DEFAULT_COMPAT_DB_PATH,
        help="Compatibility aggregate SQLite output path",
    )
    parser.add_argument(
        "--catalog-dir",
        default="",
        help=f"Optional workload subdirectory under {benchmark_sources.RUN_SRC_ROOT}",
    )
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang")
    parser.add_argument("--extra-opt-flags", default="", help="Extra flags passed to opt")
    return parser.parse_args()


def discover_workloads(root: Path, catalog_dir: str = "") -> list[benchmark_sources.CatalogWorkload]:
    return benchmark_sources.discover_catalog_workloads(root, catalog_dir)


def resolve_db_dir(root: Path, db_dir: str) -> Path:
    path = Path(db_dir)
    if not path.is_absolute():
        path = (root / db_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_db_path(root: Path, db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = (root / db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def workload_db_path(db_dir: Path, workload_id: str) -> Path:
    return db_dir / f"vfs-{workload_id}.sqlite"


def create_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE vfs (
            bench TEXT NOT NULL,
            use_vf TEXT NOT NULL,
            raw_vf TEXT NOT NULL,
            cost TEXT NOT NULL,
            compare TEXT NOT NULL,
            plan_index INTEGER,
            selected INTEGER NOT NULL,
            failure TEXT NOT NULL,
            failure_message TEXT NOT NULL,
            source TEXT NOT NULL,
            vplan_log_path TEXT NOT NULL,
            vplan_log_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (bench, use_vf)
        )
        """
    )
    conn.commit()


def insert_vf_row(
    conn: sqlite3.Connection,
    *,
    bench: str,
    use_vf: str,
    raw_vf: str,
    cost: str,
    compare: str,
    plan_index: int | None,
    selected: bool,
    failure: str,
    failure_message: str,
    source: str,
    vplan_log_path: str,
    vplan_log_text: str,
) -> None:
    conn.execute(
        """
        INSERT INTO vfs (
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
            vplan_log_text,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bench,
            use_vf,
            raw_vf,
            cost,
            compare,
            plan_index,
            1 if selected else 0,
            failure,
            failure_message,
            source,
            vplan_log_path,
            vplan_log_text,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()


def write_workload_db(db_path: Path, result: dict[str, object]) -> tuple[int, str]:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    create_table(conn)

    bench = str(result["bench"])
    log_text = str(result.get("vplan_log_text") or result.get("container_log_text") or "")
    source = str(result.get("source") or "")
    log_path = str(result.get("vplan_log") or "")

    if int(result["exit_code"]) != 0:
        insert_vf_row(
            conn,
            bench=bench,
            use_vf="",
            raw_vf="",
            cost="",
            compare="",
            plan_index=None,
            selected=False,
            failure="vplan_failed",
            failure_message="vplan-explain failed",
            source=source,
            vplan_log_path=log_path,
            vplan_log_text=log_text,
        )
        conn.close()
        return 1, "fail"

    vf_candidates = list(result["vf_candidates"])
    if not vf_candidates:
        failure = str(result.get("analysis_failure") or "no_vf")
        failure_message = str(
            result.get("analysis_failure_message")
            or "no parseable VF entries found in vplan-explain output"
        )
        insert_vf_row(
            conn,
            bench=bench,
            use_vf="",
            raw_vf="",
            cost="",
            compare="",
            plan_index=None,
            selected=False,
            failure=failure,
            failure_message=failure_message,
            source=source,
            vplan_log_path=log_path,
            vplan_log_text=log_text,
        )
        conn.close()
        return 1, "unsupported" if failure == "unsupported_analysis_source" else "no-vf"

    for candidate in vf_candidates:
        insert_vf_row(
            conn,
            bench=bench,
            use_vf=str(candidate["use_vf"]),
            raw_vf=str(candidate["raw_vf"]),
            cost=str(candidate["cost"]),
            compare=str(candidate.get("compare") or ""),
            plan_index=int(candidate["plan_index"]) if candidate["plan_index"] is not None else None,
            selected=bool(candidate["selected"]),
            failure="",
            failure_message="",
            source=source,
            vplan_log_path=log_path,
            vplan_log_text=log_text,
        )

    conn.close()
    return len(vf_candidates), f"vf={len(vf_candidates)}"


def export_aggregate_db(workload_dbs: list[Path], aggregate_db_path: Path) -> None:
    if aggregate_db_path.exists():
        aggregate_db_path.unlink()

    conn = sqlite3.connect(aggregate_db_path)
    create_table(conn)
    placeholders = ", ".join("?" for _ in VFS_COLUMNS)
    columns = ", ".join(VFS_COLUMNS)

    for workload_db in workload_dbs:
        source_conn = sqlite3.connect(workload_db)
        rows = source_conn.execute(
            f"SELECT {columns} FROM vfs ORDER BY bench, use_vf"
        ).fetchall()
        source_conn.close()
        if rows:
            conn.executemany(
                f"INSERT INTO vfs ({columns}) VALUES ({placeholders})",
                rows,
            )
            conn.commit()

    conn.close()


def main() -> None:
    args = parse_args()
    root = emulate.repo_root()
    run_id = datetime.now().strftime("%Y%m%d%H%M")
    workloads = discover_workloads(root, args.catalog_dir)
    db_dir = resolve_db_dir(root, args.db_dir)
    aggregate_db_path = emulate_all.resolve_db_path(
        root,
        args.db_path,
        run_id,
        prefix="vfs",
        arch=args.arch,
        bench_label=emulate_all.result_scope_label(args.catalog_dir, default_label="all"),
    )
    compat_db_path = resolve_db_path(root, args.compat_db_path) if args.compat_db_path else None

    vplan_explain.validate_args(args)
    vplan_explain.ensure_image_exists(args.image)

    print(
        f"vplan-explain-all: workloads={len(workloads)} catalog_dir={args.catalog_dir or '.'} "
        f"db_dir={db_dir.name} aggregate={aggregate_db_path.name}"
    )

    workload_dbs: list[Path] = []
    failures = 0
    no_vf_rows = 0
    total_rows = 0

    for index, workload in enumerate(workloads, start=1):
        result = vplan_explain.run_vplan_explain(
            bench=workload.workload_id,
            image=args.image,
            platform=args.platform,
            arch=args.arch,
            vlen=args.vlen,
            len_1d=args.len_1d,
            lmul=args.lmul,
            llvm_custom=args.llvm_custom,
            output_root=args.output_root,
            ensure_image=False,
            echo_output=False,
            x86_march=args.x86_march,
            extra_cflags=args.extra_cflags,
            extra_opt_flags=args.extra_opt_flags,
        )

        workload_db = workload_db_path(db_dir, workload.workload_id)
        row_count, status = write_workload_db(workload_db, result)
        workload_dbs.append(workload_db)
        total_rows += row_count

        if status in {"fail", "no-vf", "unsupported"}:
            failures += 1
        if status in {"no-vf", "unsupported"}:
            no_vf_rows += 1

        print(f"[vplan {index}/{len(workloads)}] {workload.workload_id} {status}")

    export_aggregate_db(workload_dbs, aggregate_db_path)
    if compat_db_path is not None and compat_db_path != aggregate_db_path:
        shutil.copyfile(aggregate_db_path, compat_db_path)
    print(
        f"done: rows={total_rows} failures={failures} no_vf={no_vf_rows} "
        f"aggregate={aggregate_db_path}"
    )


if __name__ == "__main__":
    main()
