#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    import benchmark_sources
    import emulate
    import vplan_explain
except ModuleNotFoundError:
    from scripts import benchmark_sources, emulate, vplan_explain


DEFAULT_DB_PATH = "artifacts/vfs.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run vplan-explain across all TSVC loop benchmarks and save VF candidates to SQLite."
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
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="SQLite output path for flattened VF results",
    )
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang")
    return parser.parse_args()


def discover_benches(root: Path) -> list[str]:
    return benchmark_sources.discover_catalog_benches(root)


def resolve_db_path(root: Path, db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = (root / db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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


def main() -> None:
    args = parse_args()
    root = emulate.repo_root()
    benches = discover_benches(root)
    db_path = resolve_db_path(root, args.db_path)

    if db_path.exists():
        db_path.unlink()

    vplan_explain.validate_args(args)
    vplan_explain.ensure_image_exists(args.image)

    conn = sqlite3.connect(db_path)
    create_table(conn)

    print(f"vplan-explain-all: benches={len(benches)} db={db_path.name}")
    failures = 0
    no_vf_rows = 0
    total_rows = 0

    for index, bench in enumerate(benches, start=1):
        result = vplan_explain.run_vplan_explain(
            bench=bench,
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
        )

        log_text = str(result.get("vplan_log_text") or result.get("container_log_text") or "")
        source = str(result.get("source") or "")
        log_path = str(result.get("vplan_log") or "")

        if int(result["exit_code"]) != 0:
            failures += 1
            total_rows += 1
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
            print(f"[vplan {index}/{len(benches)}] {bench} fail")
            continue

        vf_candidates = list(result["vf_candidates"])
        if not vf_candidates:
            no_vf_rows += 1
            total_rows += 1
            insert_vf_row(
                conn,
                bench=bench,
                use_vf="",
                raw_vf="",
                cost="",
                compare="",
                plan_index=None,
                selected=False,
                failure="no_vf",
                failure_message="no parseable VF entries found in vplan-explain output",
                source=source,
                vplan_log_path=log_path,
                vplan_log_text=log_text,
            )
            print(f"[vplan {index}/{len(benches)}] {bench} no-vf")
            continue

        for candidate in vf_candidates:
            total_rows += 1
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
        print(f"[vplan {index}/{len(benches)}] {bench} vf={len(vf_candidates)}")

    conn.close()
    print(f"done: rows={total_rows} failures={failures} no_vf={no_vf_rows} db={db_path}")

if __name__ == "__main__":
    main()
