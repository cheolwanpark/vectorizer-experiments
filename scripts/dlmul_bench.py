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
    root: Path,
    case_name: str,
    source_case_name: str | None = None,
    kind: str,
    phase1_total_elems: int,
    phase2_total_elems: int,
    phase3_total_elems: int,
    outer_iters: int,
    len_1d: int = 256,
    dyn_main_phase3_lmul: str = "m2",
    dyn_safe_phase3_lmul: str = "m1",
) -> tuple[VariantSpec, ...]:
    source_case_name = source_case_name or case_name

    def make_variant(name: str, phase1_lmul: str, phase2_lmul: str, phase3_lmul: str) -> VariantSpec:
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
            "source_case_name": source_case_name,
        }
        patterns = (rf"vsetvli.*{phase1_lmul}\b",)
        if phase2_lmul != phase1_lmul:
            patterns += (rf"vsetvli.*{phase2_lmul}\b",)
        if phase3_lmul not in (phase1_lmul, phase2_lmul):
            patterns += (rf"vsetvli.*{phase3_lmul}\b",)
        return VariantSpec(
            name=name,
            defines=(),
            params=params,
            asm_patterns=patterns,
            source_path=str(root / f"{source_case_name}_{name}.c"),
        )

    return (
        make_variant("fixed_m1", "m1", "m1", "m1"),
        make_variant("fixed_m2", "m2", "m2", "m2"),
        make_variant("fixed_m4", "m4", "m4", "m4"),
        make_variant("dyn_main", "m4", "m2", dyn_main_phase3_lmul),
        make_variant("dyn_safe", "m4", "m1", dyn_safe_phase3_lmul),
    )


def pressure_island_variants(
    *,
    root: Path,
    case_name: str,
    source_case_name: str | None = None,
    kind: str,
    total_elems: int,
    outer_iters: int,
    hypothesis: str,
) -> tuple[VariantSpec, ...]:
    source_case_name = source_case_name or case_name
    source_path = str(root / f"{source_case_name}.c")

    def make_variant(name: str, define_value: int, island_lmul: str, patterns: tuple[str, ...]) -> VariantSpec:
        params = {
            "kind": kind,
            "hypothesis": hypothesis,
            "phase1_lmul": "m4" if name.startswith("dyn_") else island_lmul,
            "phase2_lmul": island_lmul,
            "phase3_lmul": "m4" if name.startswith("dyn_") else island_lmul,
            "phase1_total_elems": total_elems,
            "phase2_total_elems": total_elems,
            "phase3_total_elems": total_elems,
            "outer_iters": outer_iters,
            "len_1d": 256,
            "source_case_name": source_case_name,
        }
        return VariantSpec(
            name=name,
            defines=(f"DLB_BENCH_VARIANT={define_value}",),
            params=params,
            asm_patterns=patterns,
            source_path=source_path,
        )

    return (
        make_variant("fixed_m1", 1, "m1", (r"vsetvli.*m1\b",)),
        make_variant("fixed_m2", 2, "m2", (r"vsetvli.*m2\b",)),
        make_variant("fixed_m4", 4, "m4", (r"vsetvli.*m4\b",)),
        make_variant("dyn_main", 20, "m2", (r"vsetvli.*m4\b", r"vsetvli.*m2\b", r"vsetvli.*m4\b")),
        make_variant("dyn_safe", 10, "m1", (r"vsetvli.*m4\b", r"vsetvli.*m1\b", r"vsetvli.*m4\b")),
    )


def make_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT
    return (
        CaseSpec(
            "dynamic_lmul_workload",
            "wb1",
            str(root / "wb1.c"),
            compact_variants(
                root=root,
                case_name="wb1",
                kind="fp_affine_pressure",
                phase1_total_elems=96,
                phase2_total_elems=192,
                phase3_total_elems=32,
                outer_iters=32,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb2",
            str(root / "wb6.c"),
            compact_variants(
                root=root,
                case_name="wb2",
                source_case_name="wb6",
                kind="widening_reduction_fuse",
                phase1_total_elems=96,
                phase2_total_elems=192,
                phase3_total_elems=32,
                outer_iters=24,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb3",
            str(root / "wb7.c"),
            compact_variants(
                root=root,
                case_name="wb3",
                source_case_name="wb7",
                kind="dequant_gelu_lite",
                phase1_total_elems=96,
                phase2_total_elems=192,
                phase3_total_elems=32,
                outer_iters=24,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb4",
            str(root / "wb9.c"),
            compact_variants(
                root=root,
                case_name="wb4",
                source_case_name="wb9",
                kind="segmented_pressure_rescue",
                phase1_total_elems=96,
                phase2_total_elems=192,
                phase3_total_elems=32,
                outer_iters=28,
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb5",
            str(root / "wb10.c"),
            pressure_island_variants(
                root=root,
                case_name="wb5",
                source_case_name="wb10",
                kind="wide_envelope_pressure_island",
                total_elems=224,
                outer_iters=28,
                hypothesis="m4 load/precompute and m4 epilogue amortize loop cost while m2 island avoids live-temp pressure",
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb6",
            str(root / "wb11.c"),
            pressure_island_variants(
                root=root,
                case_name="wb6",
                source_case_name="wb11",
                kind="dual_pressure_island",
                total_elems=192,
                outer_iters=30,
                hypothesis="two register-heavy islands benefit from narrowed LMUL without giving up m4 between islands",
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb7",
            str(root / "wb12.c"),
            pressure_island_variants(
                root=root,
                case_name="wb7",
                source_case_name="wb12",
                kind="many_input_fanout",
                total_elems=224,
                outer_iters=24,
                hypothesis="many m4 input streams favor wide loads, but fanout temporaries favor m2 compute",
            ),
        ),
        CaseSpec(
            "dynamic_lmul_workload",
            "wb8",
            str(root / "wb13.c"),
            pressure_island_variants(
                root=root,
                case_name="wb8",
                source_case_name="wb13",
                kind="wide_epilogue_after_pressure",
                total_elems=256,
                outer_iters=22,
                hypothesis="narrow dependency chain reduces pressure, then m4 epilogue keeps wide postcompute and store efficient",
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
