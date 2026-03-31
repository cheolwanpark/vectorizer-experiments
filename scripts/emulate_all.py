#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import emulate
    import vplan_explain
except ModuleNotFoundError:
    from scripts import emulate, vplan_explain


DEFAULT_DB_DIR = "artifacts"
DEFAULT_SAMPLES = 10
DEFAULT_CONCURRENCY = 10

TABLE_COLUMNS = [
    "run_id",
    "created_at",
    "stage",
    "failure",
    "failure_message",
    "bench",
    "use_vf",
    "sample_index",
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
    "run_log",
    "trace_file",
    "report_file",
    "docker_command",
    "source",
    "vplan_log_path",
    "vplan_log_text",
    "container_log_text",
    "run_log_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run vplan-explain and emulate across all TSVC loop benchmarks."
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
    parser.add_argument("--arch", default="RVV", choices=["RVV", "MAC"], help="Target architecture")
    parser.add_argument("--vlen", type=int, default=128, help="RVV vector length in bits")
    parser.add_argument("--llvm-custom", default="", help="Optional host LLVM build/bin directory")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel sample count")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="Samples per bench/VF")
    parser.add_argument(
        "--db-dir",
        default=DEFAULT_DB_DIR,
        help="Directory for emulate-result-YYYYMMDDHHMM.sqlite",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    emulate.validate_positive_int("len", args.len_1d)
    emulate.validate_positive_int("lmul", args.lmul)
    emulate.validate_positive_int("timeout", args.timeout)
    emulate.validate_positive_int("concurrency", args.concurrency)
    emulate.validate_positive_int("samples", args.samples)
    if args.arch == "RVV" and args.vlen <= 0:
        emulate.fail("vlen must be a positive integer")


def discover_benches(root: Path) -> list[str]:
    loops_root = root / "emulator" / "benchmarks" / "TSVC_2" / "src" / "loops"
    return sorted(path.stem for path in loops_root.glob("s*.c"))


def resolve_db_path(root: Path, db_dir: str, run_id: str) -> Path:
    db_root = Path(db_dir)
    if not db_root.is_absolute():
        db_root = (root / db_dir).resolve()
    db_root.mkdir(parents=True, exist_ok=True)
    return db_root / f"emulate-result-{run_id}.sqlite"


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
            sample_index INTEGER NOT NULL,
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
            run_log TEXT,
            trace_file TEXT,
            report_file TEXT,
            docker_command TEXT,
            source TEXT,
            vplan_log_path TEXT,
            vplan_log_text TEXT,
            container_log_text TEXT,
            run_log_text TEXT,
            PRIMARY KEY (bench, use_vf, sample_index)
        )
        """
    )
    conn.commit()


def make_empty_row(run_id: str, bench: str, use_vf: str, sample_index: int) -> dict[str, Any]:
    row = {column: None for column in TABLE_COLUMNS}
    row["run_id"] = run_id
    row["created_at"] = datetime.now().isoformat(timespec="seconds")
    row["stage"] = ""
    row["failure"] = ""
    row["failure_message"] = ""
    row["bench"] = bench
    row["use_vf"] = use_vf
    row["sample_index"] = sample_index
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


def make_vplan_failure_row(
    *,
    run_id: str,
    bench: str,
    args: argparse.Namespace,
    failure: str,
    message: str,
    vplan_result: dict[str, Any],
) -> dict[str, Any]:
    row = make_empty_row(run_id, bench, "", 0)
    row.update(
        {
            "stage": "vplan",
            "failure": failure,
            "failure_message": message,
            "benchmark": bench,
            "image": args.image,
            "len_1d": args.len_1d,
            "lmul": args.lmul,
            "timeout_s": args.timeout,
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
    sample_index: int,
    args: argparse.Namespace,
    vplan_result: dict[str, Any],
    emulate_result: dict[str, Any] | None,
    failure: str = "",
    failure_message: str = "",
) -> dict[str, Any]:
    row = make_empty_row(run_id, bench, use_vf, sample_index)
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
    row["sample_index"] = sample_index
    row["container_log_text"] = emulate_result.get("container_log_text", "")
    row["run_log_text"] = emulate_result.get("run_log_text", "")
    return row


def run_sample(
    *,
    bench: str,
    use_vf: str,
    sample_index: int,
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
    )


def main() -> None:
    args = parse_args()
    validate_args(args)

    root = emulate.repo_root()
    run_id = datetime.now().strftime("%Y%m%d%H%M")
    db_path = resolve_db_path(root, args.db_dir, run_id)
    benches = discover_benches(root)

    emulate.ensure_image_exists(args.image)

    conn = sqlite3.connect(db_path)
    create_table(conn)

    print(f"SQLite:     {db_path}")
    print(f"Benchmarks: {len(benches)}")
    print(f"Samples:    {args.samples}")
    print(f"Parallel:   {args.concurrency}")

    scheduled: list[tuple[str, str, int, dict[str, Any]]] = []
    any_failure = False

    for index, bench in enumerate(benches, start=1):
        print(f"[vplan {index}/{len(benches)}] {bench}")
        vplan_result = vplan_explain.run_vplan_explain(
            bench=bench,
            image=args.image,
            platform=emulate.DEFAULT_PLATFORM,
            arch=args.arch,
            vlen=args.vlen,
            llvm_custom=args.llvm_custom,
            output_root=args.vplan_log_root,
            ensure_image=False,
        )
        if int(vplan_result["exit_code"]) != 0:
            any_failure = True
            insert_row(
                conn,
                make_vplan_failure_row(
                    run_id=run_id,
                    bench=bench,
                    args=args,
                    failure="vplan_failed",
                    message="vplan-explain failed",
                    vplan_result=vplan_result,
                ),
            )
            continue

        vf_candidates = [candidate["use_vf"] for candidate in vplan_result["vf_candidates"]]
        if not vf_candidates:
            any_failure = True
            insert_row(
                conn,
                make_vplan_failure_row(
                    run_id=run_id,
                    bench=bench,
                    args=args,
                    failure="no_vf",
                    message="no parseable VF entries found in vplan-explain output",
                    vplan_result=vplan_result,
                ),
            )
            continue

        for use_vf in vf_candidates:
            for sample_index in range(1, args.samples + 1):
                scheduled.append((bench, use_vf, sample_index, vplan_result))

    print(f"Queued emulate jobs: {len(scheduled)}")

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_map = {
            executor.submit(
                run_sample,
                bench=bench,
                use_vf=use_vf,
                sample_index=sample_index,
                args=args,
            ): (bench, use_vf, sample_index, vplan_result)
            for bench, use_vf, sample_index, vplan_result in scheduled
        }

        for future in as_completed(future_map):
            bench, use_vf, sample_index, vplan_result = future_map[future]
            try:
                emulate_result = future.result()
            except Exception as exc:
                any_failure = True
                row = make_emulate_row(
                    run_id=run_id,
                    bench=bench,
                    use_vf=use_vf,
                    sample_index=sample_index,
                    args=args,
                    vplan_result=vplan_result,
                    emulate_result=None,
                    failure="emulate_exception",
                    failure_message=str(exc),
                )
                insert_row(conn, row)
                print(f"[FAIL] {bench} {use_vf} sample={sample_index}: {exc}")
                continue

            failure = ""
            failure_message = ""
            if emulate_result["failed"]:
                any_failure = True
                failure = "emulate_failed"
                failure_message = str(emulate_result["summary"].get("status", "emulate failed"))

            row = make_emulate_row(
                run_id=run_id,
                bench=bench,
                use_vf=use_vf,
                sample_index=sample_index,
                args=args,
                vplan_result=vplan_result,
                emulate_result=emulate_result,
                failure=failure,
                failure_message=failure_message,
            )
            insert_row(conn, row)
            print(f"[done] {bench} {use_vf} sample={sample_index} status={row.get('status')}")

    conn.close()

    if any_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
