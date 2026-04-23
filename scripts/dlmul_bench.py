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


def lmul_patterns(*lmuls: str) -> tuple[str, ...]:
    patterns: list[str] = []
    previous = ""
    for lmul in lmuls:
        if lmul != previous:
            patterns.append(rf"vsetvli.*{lmul}\b")
        previous = lmul
    return tuple(patterns)


def db_variant(
    *,
    root: Path,
    source_name: str,
    name: str,
    define_value: str,
    kind: str,
    phase_lmuls: tuple[str, str, str],
    phase_totals: tuple[int, int, int],
    outer_iters: int,
    hypothesis: str,
    extra_defines: tuple[str, ...] = (),
) -> VariantSpec:
    return VariantSpec(
        name=name,
        defines=(f"DLB_BENCH_VARIANT={define_value}",) + extra_defines,
        params={
            "kind": kind,
            "hypothesis": hypothesis,
            "phase1_lmul": phase_lmuls[0],
            "phase2_lmul": phase_lmuls[1],
            "phase3_lmul": phase_lmuls[2],
            "phase1_total_elems": phase_totals[0],
            "phase2_total_elems": phase_totals[1],
            "phase3_total_elems": phase_totals[2],
            "outer_iters": outer_iters,
            "len_1d": 256,
            "source_case_name": source_name,
        },
        asm_patterns=lmul_patterns(*phase_lmuls),
        source_path=str(root / f"{source_name}.c"),
    )


def db_case(
    *,
    root: Path,
    case_name: str,
    source_name: str,
    variants: tuple[VariantSpec, ...],
) -> CaseSpec:
    return CaseSpec(
        "dynamic_lmul_workload",
        case_name,
        str(root / f"{source_name}.c"),
        variants,
    )


def make_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT
    db1_hypothesis = "m4 stream envelope plus m2 e16-to-e32 widening accumulator island"
    db2_hypothesis = "m8 stream envelope with a high-live-temp m2 f32 FMA island"
    db3_hypothesis = "dynamic m4/m2/m4 improves as the widening pressure island grows"
    db4_hypothesis = "dequantized dot core uses m2 widening pressure with m4 setup and epilogue"
    db5_hypothesis = "wide-only control should prefer fixed m8 or m4 over unnecessary switching"
    db6_hypothesis = "one-way m8 setup to m2 widening core avoids returning to wide epilogue"
    db7_hypothesis = "m8 stream envelope plus m2 FIR/FMA bank should punish fixed m8 pressure"
    db8_hypothesis = "dynamic m8/m2/m8 should improve as repeated FMA pressure grows"
    db9_hypothesis = "m8 color load with m2 polynomial pressure and m4 store"
    db10_hypothesis = "wide-only control should still favor fixed m8 over unnecessary m2 middle phase"

    return (
        db_case(
            root=root,
            case_name="db1",
            source_name="db1",
            variants=(
                db_variant(
                    root=root,
                    source_name="db1",
                    name="fixed_m1",
                    define_value="DLB_VARIANT_FIXED_M1",
                    kind="wide_stream_widening_acc8",
                    phase_lmuls=("m1", "m1", "m1"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db1_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db1",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="wide_stream_widening_acc8",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db1_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db1",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="wide_stream_widening_acc8",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db1_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db1",
                    name="dyn_m4_m2_m4",
                    define_value="DLB_VARIANT_DYN_M4_M2_M4",
                    kind="wide_stream_widening_acc8",
                    phase_lmuls=("m4", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db1_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db2",
            source_name="db2",
            variants=(
                db_variant(
                    root=root,
                    source_name="db2",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="m8_stream_m2_fma_island",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(128, 128, 128),
                    outer_iters=40,
                    hypothesis=db2_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db2",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="m8_stream_m2_fma_island",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(128, 128, 128),
                    outer_iters=40,
                    hypothesis=db2_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db2",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="m8_stream_m2_fma_island",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(128, 128, 128),
                    outer_iters=40,
                    hypothesis=db2_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db2",
                    name="dyn_m8_m2_m8",
                    define_value="DLB_VARIANT_DYN_M8_M2_M8",
                    kind="m8_stream_m2_fma_island",
                    phase_lmuls=("m8", "m2", "m8"),
                    phase_totals=(128, 128, 128),
                    outer_iters=40,
                    hypothesis=db2_hypothesis,
                ),
            ),
        ),
        *tuple(
            db_case(
                root=root,
                case_name=case_name,
                source_name="db3",
                variants=(
                    db_variant(
                        root=root,
                        source_name="db3",
                        name="fixed_m2",
                        define_value="DLB_VARIANT_FIXED_M2",
                        kind="phase_length_sweep",
                        phase_lmuls=("m2", "m2", "m2"),
                        phase_totals=(128, phase_b_elems, 128),
                        outer_iters=32,
                        hypothesis=db3_hypothesis,
                        extra_defines=(f"DB3_PHASE_B_ELEMS={phase_b_elems}",),
                    ),
                    db_variant(
                        root=root,
                        source_name="db3",
                        name="fixed_m4",
                        define_value="DLB_VARIANT_FIXED_M4",
                        kind="phase_length_sweep",
                        phase_lmuls=("m4", "m4", "m4"),
                        phase_totals=(128, phase_b_elems, 128),
                        outer_iters=32,
                        hypothesis=db3_hypothesis,
                        extra_defines=(f"DB3_PHASE_B_ELEMS={phase_b_elems}",),
                    ),
                    db_variant(
                        root=root,
                        source_name="db3",
                        name="dyn_m4_m2_m4",
                        define_value="DLB_VARIANT_DYN_M4_M2_M4",
                        kind="phase_length_sweep",
                        phase_lmuls=("m4", "m2", "m4"),
                        phase_totals=(128, phase_b_elems, 128),
                        outer_iters=32,
                        hypothesis=db3_hypothesis,
                        extra_defines=(f"DB3_PHASE_B_ELEMS={phase_b_elems}",),
                    ),
                ),
            )
            for case_name, phase_b_elems in (
                ("db3-short", 32),
                ("db3-medium", 96),
                ("db3-long", 192),
            )
        ),
        db_case(
            root=root,
            case_name="db4",
            source_name="db4",
            variants=(
                db_variant(
                    root=root,
                    source_name="db4",
                    name="fixed_m1",
                    define_value="DLB_VARIANT_FIXED_M1",
                    kind="dequant_dot_widening_core",
                    phase_lmuls=("m1", "m1", "m1"),
                    phase_totals=(192, 192, 192),
                    outer_iters=30,
                    hypothesis=db4_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db4",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="dequant_dot_widening_core",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=30,
                    hypothesis=db4_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db4",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="dequant_dot_widening_core",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=30,
                    hypothesis=db4_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db4",
                    name="dyn_m4_m2_m4",
                    define_value="DLB_VARIANT_DYN_M4_M2_M4",
                    kind="dequant_dot_widening_core",
                    phase_lmuls=("m4", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=30,
                    hypothesis=db4_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db5",
            source_name="db5",
            variants=(
                db_variant(
                    root=root,
                    source_name="db5",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="wide_only_negative_control",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=36,
                    hypothesis=db5_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db5",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="wide_only_negative_control",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=36,
                    hypothesis=db5_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db5",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="wide_only_negative_control",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(192, 192, 192),
                    outer_iters=36,
                    hypothesis=db5_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db5",
                    name="dyn_m8_m2_m8",
                    define_value="DLB_VARIANT_DYN_M8_M2_M8",
                    kind="wide_only_negative_control",
                    phase_lmuls=("m8", "m2", "m8"),
                    phase_totals=(192, 192, 192),
                    outer_iters=36,
                    hypothesis=db5_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db6",
            source_name="db6",
            variants=(
                db_variant(
                    root=root,
                    source_name="db6",
                    name="fixed_m1",
                    define_value="DLB_VARIANT_FIXED_M1",
                    kind="one_way_dequant_gemv_tile",
                    phase_lmuls=("m1", "m1", "m1"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db6_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db6",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="one_way_dequant_gemv_tile",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db6_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db6",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="one_way_dequant_gemv_tile",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db6_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db6",
                    name="dyn_m8_m2_m2",
                    define_value="DLB_VARIANT_DYN_M8_M2_M2",
                    kind="one_way_dequant_gemv_tile",
                    phase_lmuls=("m8", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db6_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db6",
                    name="dyn_m8_m2_m4",
                    define_value="DLB_VARIANT_DYN_M8_M2_M4",
                    kind="one_way_dequant_gemv_tile",
                    phase_lmuls=("m8", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db6_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db7",
            source_name="db7",
            variants=(
                db_variant(
                    root=root,
                    source_name="db7",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="fir_fma_pressure_bank",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(128, 128, 128),
                    outer_iters=36,
                    hypothesis=db7_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db7",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="fir_fma_pressure_bank",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(128, 128, 128),
                    outer_iters=36,
                    hypothesis=db7_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db7",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="fir_fma_pressure_bank",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(128, 128, 128),
                    outer_iters=36,
                    hypothesis=db7_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db7",
                    name="dyn_m8_m2_m4",
                    define_value="DLB_VARIANT_DYN_M8_M2_M4",
                    kind="fir_fma_pressure_bank",
                    phase_lmuls=("m8", "m2", "m4"),
                    phase_totals=(128, 128, 128),
                    outer_iters=36,
                    hypothesis=db7_hypothesis,
                ),
            ),
        ),
        *tuple(
            db_case(
                root=root,
                case_name=case_name,
                source_name="db8",
                variants=(
                    db_variant(
                        root=root,
                        source_name="db8",
                        name="fixed_m2",
                        define_value="DLB_VARIANT_FIXED_M2",
                        kind="hysteresis_pressure_sweep",
                        phase_lmuls=("m2", "m2", "m2"),
                        phase_totals=(128, 128 * repeats, 128),
                        outer_iters=28,
                        hypothesis=db8_hypothesis,
                        extra_defines=(f"DB8_PRESSURE_REPEATS={repeats}",),
                    ),
                    db_variant(
                        root=root,
                        source_name="db8",
                        name="fixed_m4",
                        define_value="DLB_VARIANT_FIXED_M4",
                        kind="hysteresis_pressure_sweep",
                        phase_lmuls=("m4", "m4", "m4"),
                        phase_totals=(128, 128 * repeats, 128),
                        outer_iters=28,
                        hypothesis=db8_hypothesis,
                        extra_defines=(f"DB8_PRESSURE_REPEATS={repeats}",),
                    ),
                    db_variant(
                        root=root,
                        source_name="db8",
                        name="fixed_m8",
                        define_value="DLB_VARIANT_FIXED_M8",
                        kind="hysteresis_pressure_sweep",
                        phase_lmuls=("m8", "m8", "m8"),
                        phase_totals=(128, 128 * repeats, 128),
                        outer_iters=28,
                        hypothesis=db8_hypothesis,
                        extra_defines=(f"DB8_PRESSURE_REPEATS={repeats}",),
                    ),
                    db_variant(
                        root=root,
                        source_name="db8",
                        name="dyn_m8_m2_m8",
                        define_value="DLB_VARIANT_DYN_M8_M2_M8",
                        kind="hysteresis_pressure_sweep",
                        phase_lmuls=("m8", "m2", "m8"),
                        phase_totals=(128, 128 * repeats, 128),
                        outer_iters=28,
                        hypothesis=db8_hypothesis,
                        extra_defines=(f"DB8_PRESSURE_REPEATS={repeats}",),
                    ),
                ),
            )
            for case_name, repeats in (
                ("db8-short", 1),
                ("db8-medium", 2),
                ("db8-long", 4),
            )
        ),
        db_case(
            root=root,
            case_name="db9",
            source_name="db9",
            variants=(
                db_variant(
                    root=root,
                    source_name="db9",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="gamma_polynomial_pressure",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(128, 128, 128),
                    outer_iters=34,
                    hypothesis=db9_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db9",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="gamma_polynomial_pressure",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(128, 128, 128),
                    outer_iters=34,
                    hypothesis=db9_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db9",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="gamma_polynomial_pressure",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(128, 128, 128),
                    outer_iters=34,
                    hypothesis=db9_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db9",
                    name="dyn_m8_m2_m4",
                    define_value="DLB_VARIANT_DYN_M8_M2_M4",
                    kind="gamma_polynomial_pressure",
                    phase_lmuls=("m8", "m2", "m4"),
                    phase_totals=(128, 128, 128),
                    outer_iters=34,
                    hypothesis=db9_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db10",
            source_name="db10",
            variants=(
                db_variant(
                    root=root,
                    source_name="db10",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="wide_only_control2",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(224, 224, 224),
                    outer_iters=32,
                    hypothesis=db10_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db10",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="wide_only_control2",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(224, 224, 224),
                    outer_iters=32,
                    hypothesis=db10_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db10",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="wide_only_control2",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(224, 224, 224),
                    outer_iters=32,
                    hypothesis=db10_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db10",
                    name="dyn_m8_m2_m8",
                    define_value="DLB_VARIANT_DYN_M8_M2_M8",
                    kind="wide_only_control2",
                    phase_lmuls=("m8", "m2", "m8"),
                    phase_totals=(224, 224, 224),
                    outer_iters=32,
                    hypothesis=db10_hypothesis,
                ),
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
