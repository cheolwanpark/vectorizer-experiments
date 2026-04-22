#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

try:
    if __package__:
        from . import dlmul_runner, emulate
        from .dlmul_runner import (
            CaseSpec,
            VariantSpec,
            benchmark_id,
            build_extra_cflags,
            iter_selected_jobs,
            make_exception_row,
            make_row_from_emulate_result,
            ordered_patterns_match,
            run_job,
        )
    else:
        import dlmul_runner
        import emulate
        from dlmul_runner import (
            CaseSpec,
            VariantSpec,
            benchmark_id,
            build_extra_cflags,
            iter_selected_jobs,
            make_exception_row,
            make_row_from_emulate_result,
            ordered_patterns_match,
            run_job,
        )
except ModuleNotFoundError:
    from scripts import dlmul_runner, emulate
    from scripts.dlmul_runner import (
        CaseSpec,
        VariantSpec,
        benchmark_id,
        build_extra_cflags,
        iter_selected_jobs,
        make_exception_row,
        make_row_from_emulate_result,
        ordered_patterns_match,
        run_job,
    )


DEFAULT_DB_PATH = "artifacts/dlmul-bench.sqlite"
DEFAULT_LOG_ROOT = "artifacts/dlmul-bench"
DEFAULT_CONCURRENCY = dlmul_runner.DEFAULT_CONCURRENCY
DEFAULT_TIMEOUT = dlmul_runner.DEFAULT_TIMEOUT
CATALOG_ROOT = Path("emulator") / "run" / "src" / "bench" / "dlmul"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run C-based dynamic LMUL workload benches through emulate.py and save results to SQLite."
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


def create_table(conn: sqlite3.Connection) -> None:
    dlmul_runner.create_table(conn, "dlmul_bench_results")


def compact_variants(
    *,
    kind: str,
    phase1_total_elems: int,
    phase2_total_elems: int,
    phase3_total_elems: int,
    outer_iters: int,
    len_1d: int = 256,
    dyn_main_phase3_lmul: str = "m2",
    dyn_safe_phase3_lmul: str = "m1",
) -> tuple[VariantSpec, ...]:
    def make_variant(name: str, phase1_lmul: str, phase2_lmul: str, phase3_lmul: str) -> VariantSpec:
        lmul_values = {"m1": 1, "m2": 2, "m4": 4}
        defines = (
            f"DLB_PHASE1_VARIANT={lmul_values[phase1_lmul]}",
            f"DLB_PHASE2_VARIANT={lmul_values[phase2_lmul]}",
            f"DLB_PHASE3_VARIANT={lmul_values[phase3_lmul]}",
            f"DLB_PHASE1_TOTAL_ELEMS={phase1_total_elems}",
            f"DLB_PHASE2_TOTAL_ELEMS={phase2_total_elems}",
            f"DLB_PHASE3_TOTAL_ELEMS={phase3_total_elems}",
            f"DLB_OUTER_ITERS={outer_iters}",
        )
        params = {
            "kind": kind,
            "phase1_lmul": phase1_lmul,
            "phase2_lmul": phase2_lmul,
            "phase3_lmul": phase3_lmul,
            "phase1_total_elems": phase1_total_elems,
            "phase2_total_elems": phase2_total_elems,
            "phase3_total_elems": phase3_total_elems,
            "outer_iters": outer_iters,
            "len_1d": len_1d,
        }
        patterns = (rf"vsetvli.*{phase1_lmul}\b",)
        if phase2_lmul != phase1_lmul:
            patterns += (rf"vsetvli.*{phase2_lmul}\b",)
        return VariantSpec(
            name=name,
            defines=defines,
            params=params,
            asm_patterns=patterns,
        )

    return (
        make_variant("fixed_m1", "m1", "m1", "m1"),
        make_variant("fixed_m2", "m2", "m2", "m2"),
        make_variant("fixed_m4", "m4", "m4", "m4"),
        make_variant("dyn_main", "m4", "m2", dyn_main_phase3_lmul),
        make_variant("dyn_safe", "m4", "m1", dyn_safe_phase3_lmul),
    )


def make_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT
    return (
        CaseSpec(
            "dynamic_lmul_workload",
            "wb1-fir32",
            str(root / "wb1_fir32.c"),
            compact_variants(
                kind="fir32",
                phase1_total_elems=256,
                phase2_total_elems=128,
                phase3_total_elems=16,
                outer_iters=32,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb2-stencil2d",
            str(root / "wb2_stencil2d.c"),
            compact_variants(
                kind="stencil2d",
                phase1_total_elems=256,
                phase2_total_elems=128,
                phase3_total_elems=16,
                outer_iters=24,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb3-layernorm",
            str(root / "wb3_layernorm.c"),
            compact_variants(
                kind="layernorm",
                phase1_total_elems=256,
                phase2_total_elems=128,
                phase3_total_elems=16,
                outer_iters=32,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb4-dequant-gemv",
            str(root / "wb4_dequant_gemv.c"),
            compact_variants(
                kind="dequant_gemv",
                phase1_total_elems=256,
                phase2_total_elems=128,
                phase3_total_elems=16,
                outer_iters=24,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb5-widening-rescue",
            str(root / "wb5_widening_rescue.c"),
            compact_variants(
                kind="widening_rescue",
                phase1_total_elems=64,
                phase2_total_elems=128,
                phase3_total_elems=64,
                outer_iters=24,
                dyn_main_phase3_lmul="m4",
                dyn_safe_phase3_lmul="m4",
            ),
        ),
    )


def main() -> None:
    args = parse_args()
    dlmul_runner.run_suite(
        args=args,
        manifest=make_manifest(),
        table_name="dlmul_bench_results",
        suite_label="dlmul-bench",
    )


if __name__ == "__main__":
    main()
