#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import benchmark_sources
    import emulate
    import emulate_all
    import profile as profile_mod
except ModuleNotFoundError:
    from scripts import benchmark_sources, emulate, emulate_all
    from scripts import profile as profile_mod


DEFAULT_DB_DIR = "artifacts"
DEFAULT_CONCURRENCY = 1
DEFAULT_VFS_DB = "artifacts/vfs.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile all TSVC benchmarks natively on x86 using precomputed VF candidates."
    )
    parser.add_argument("--image", default=profile_mod.DEFAULT_IMAGE, help="Docker image tag")
    parser.add_argument("--len", dest="len_1d", type=int, default=4096, help="LEN_1D value")
    parser.add_argument("--lmul", type=int, default=1, help="LMUL value")
    parser.add_argument("--llvm-custom", default="", help="Host LLVM build/bin directory")
    parser.add_argument("--x86-march", default=profile_mod.llvm_pipeline.DEFAULT_INTEL_TARGET_MARCH, help="x86 -march value")
    parser.add_argument("--warmup", type=int, default=profile_mod.DEFAULT_WARMUP, help="Warmup iterations")
    parser.add_argument("--repeat", type=int, default=profile_mod.DEFAULT_REPEAT, help="Timed iterations")
    parser.add_argument("--log-root", default=profile_mod.DEFAULT_LOG_ROOT, help="Host output root")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel job count")
    parser.add_argument("--db-dir", default=DEFAULT_DB_DIR, help="Directory for profile-result-*.sqlite")
    parser.add_argument("--vfs-db", default=DEFAULT_VFS_DB, help="Path to vfs.db from vplan-explain-all")
    parser.add_argument("--extra-cflags", default="", help="Extra flags passed to clang")
    parser.add_argument("--extra-opt-flags", default="", help="Extra flags passed to opt")
    return parser.parse_args()


def run_profile_job(
    *,
    bench: str,
    use_vf: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return profile_mod.run_profile(
        bench=bench,
        image=args.image,
        len_1d=args.len_1d,
        lmul=args.lmul,
        use_vf=use_vf,
        llvm_custom=args.llvm_custom,
        x86_march=args.x86_march,
        warmup=args.warmup,
        repeat=args.repeat,
        log_root=args.log_root,
        ensure_image=False,
        extra_cflags=args.extra_cflags,
        extra_opt_flags=args.extra_opt_flags,
    )


def make_profile_row(
    *,
    run_id: str,
    bench: str,
    use_vf: str,
    args: argparse.Namespace,
    vplan_result: dict[str, Any],
    profile_result: dict[str, Any] | None,
    failure: str = "",
    failure_message: str = "",
) -> dict[str, Any]:
    row = emulate_all.make_empty_row(run_id, bench, use_vf)
    row.update({
        "stage": "profile",
        "failure": failure,
        "failure_message": failure_message,
        "benchmark": bench,
        "image": getattr(args, "image", ""),
        "len_1d": args.len_1d,
        "lmul": args.lmul,
        "simulator_target": "x86_native",
        "vplan_log_path": vplan_result.get("vplan_log"),
        "vplan_log_text": vplan_result.get("vplan_log_text") or vplan_result.get("container_log_text"),
    })
    if profile_result is None:
        row["status"] = "ERROR"
        return row

    summary = profile_result["summary"]
    row.update(summary)
    row["bench"] = bench
    row["use_vf"] = use_vf
    row["container_log_text"] = profile_result.get("container_log_text", "")
    row["run_detail"] = profile_result.get("run_detail", "")
    row["opt_ll_text"] = str(profile_result.get("opt_ll_text", "") or "")
    row["asm_text"] = str(profile_result.get("asm_text", "") or "")
    return row


def main() -> None:
    args = parse_args()
    emulate.validate_positive_int("len", args.len_1d)
    emulate.validate_positive_int("lmul", args.lmul)
    emulate.validate_positive_int("concurrency", args.concurrency)

    root = emulate.repo_root()
    run_id = datetime.now().strftime("%Y%m%d%H%M")
    db_path = emulate_all.resolve_db_path(root, args.db_dir, run_id).with_name(
        f"profile-result-{run_id}.sqlite"
    )
    benches = benchmark_sources.discover_catalog_benches(root)

    emulate.ensure_image_exists(args.image)

    conn = sqlite3.connect(db_path)
    emulate_all.create_table(conn)

    print(f"profile-all: benches={len(benches)} parallel={args.concurrency} db={db_path.name}")

    vfs_db_path = emulate_all.resolve_input_path(root, args.vfs_db)
    candidates_by_bench, failures_by_bench = emulate_all.load_vfs_data(vfs_db_path)

    scheduled: list[tuple[str, str, dict[str, Any]]] = []
    vplan_failures = 0

    for index, bench in enumerate(benches, start=1):
        failure_record = failures_by_bench.get(bench)
        if failure_record is not None:
            vplan_failures += 1
            emulate_all.insert_row(
                conn,
                emulate_all.make_vplan_failure_row(
                    run_id=run_id,
                    bench=bench,
                    args=args,
                    failure=str(failure_record["failure"] or "vplan_failed"),
                    message=str(failure_record["failure_message"] or "vplan-explain failed"),
                    vplan_result=emulate_all.make_vplan_result(failure_record),
                ),
            )
            status_text = "no-vf" if failure_record["failure"] == "no_vf" else "fail"
            print(f"[vplan {index}/{len(benches)}] {bench} {status_text}")
            continue

        candidate_records = candidates_by_bench.get(bench, [])
        if not candidate_records:
            vplan_failures += 1
            emulate_all.insert_row(
                conn,
                emulate_all.make_vplan_failure_row(
                    run_id=run_id,
                    bench=bench,
                    args=args,
                    failure="missing_vfs_entry",
                    message="benchmark missing from vfs.db",
                    vplan_result=emulate_all.make_vplan_result({}),
                ),
            )
            print(f"[vplan {index}/{len(benches)}] {bench} missing")
            continue

        print(f"[vplan {index}/{len(benches)}] {bench} vf={len(candidate_records)}")
        for candidate_record in candidate_records:
            scheduled.append((bench, str(candidate_record["use_vf"]), emulate_all.make_vplan_result(candidate_record)))
        scheduled.append((bench, "", emulate_all.make_default_vplan_result()))

    print(f"profile-jobs: {len(scheduled)}")

    completed = 0
    total_jobs = len(scheduled)
    profile_failures = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_map = {
            executor.submit(
                run_profile_job,
                bench=bench,
                use_vf=use_vf,
                args=args,
            ): (bench, use_vf, vplan_result)
            for bench, use_vf, vplan_result in scheduled
        }

        for future in as_completed(future_map):
            bench, use_vf, vplan_result = future_map[future]
            completed += 1
            try:
                profile_result = future.result()
            except Exception as exc:
                profile_failures += 1
                row = make_profile_row(
                    run_id=run_id,
                    bench=bench,
                    use_vf=use_vf,
                    args=args,
                    vplan_result=vplan_result,
                    profile_result=None,
                    failure="profile_exception",
                    failure_message=str(exc),
                )
                emulate_all.insert_row(conn, row)
                print(f"[prof {completed}/{total_jobs}] {bench} {use_vf} fail")
                continue

            failure = ""
            failure_message = ""
            if profile_result["failed"]:
                profile_failures += 1
                failure = "profile_failed"
                failure_message = str(profile_result["summary"].get("status", "profile failed"))

            row = make_profile_row(
                run_id=run_id,
                bench=bench,
                use_vf=use_vf,
                args=args,
                vplan_result=vplan_result,
                profile_result=profile_result,
                failure=failure,
                failure_message=failure_message,
            )
            emulate_all.insert_row(conn, row)
            status_text = "fail" if failure else str(row.get("status", "done")).lower()
            print(f"[prof {completed}/{total_jobs}] {bench} {use_vf} {status_text}")

    conn.close()
    print(
        f"done: vplan_failures={vplan_failures} profile_failures={profile_failures} "
        f"db={db_path}"
    )

    if vplan_failures or profile_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
