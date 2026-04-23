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
DEFAULT_CASE_NAMES = ("db1", "db11", "db12", "db8-medium", "db9")
DEFAULT_SUITE = "dynamic_lmul_workload"


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


def retag_manifest(manifest: tuple[CaseSpec, ...], suite: str) -> tuple[CaseSpec, ...]:
    return tuple(
        CaseSpec(suite, case.case_name, case.source_path, case.variants)
        for case in manifest
    )


def select_cases(manifest: tuple[CaseSpec, ...], case_names: tuple[str, ...], suite: str) -> tuple[CaseSpec, ...]:
    by_name = {case.case_name: case for case in manifest}
    return retag_manifest(tuple(by_name[name] for name in case_names), suite)


def make_catalog_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT
    db1_hypothesis = "independent control: m4 stream envelope plus m2 e16-to-e32 widening accumulator island"
    db8_hypothesis = "retained m8/m2/m8 dependent negative/control case"
    db9_hypothesis = "m8 color load with m2 polynomial pressure and m4 store"
    db11_hypothesis = "m4 color polynomial chain with a dependent m2 pressure island"
    db12_hypothesis = "m4 normalized force chain with dependent m2 sqrt/div island"

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
                    kind="independent_control_wide_stream_widening_acc8",
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
                    kind="independent_control_wide_stream_widening_acc8",
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
                    kind="independent_control_wide_stream_widening_acc8",
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
                    kind="independent_control_wide_stream_widening_acc8",
                    phase_lmuls=("m4", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=32,
                    hypothesis=db1_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db8-medium",
            source_name="db8",
            variants=(
                db_variant(
                    root=root,
                    source_name="db8",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="hysteresis_pressure_sweep",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(128, 256, 128),
                    outer_iters=28,
                    hypothesis=db8_hypothesis,
                    extra_defines=("DB8_PRESSURE_REPEATS=2",),
                ),
                db_variant(
                    root=root,
                    source_name="db8",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="hysteresis_pressure_sweep",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(128, 256, 128),
                    outer_iters=28,
                    hypothesis=db8_hypothesis,
                    extra_defines=("DB8_PRESSURE_REPEATS=2",),
                ),
                db_variant(
                    root=root,
                    source_name="db8",
                    name="fixed_m8",
                    define_value="DLB_VARIANT_FIXED_M8",
                    kind="hysteresis_pressure_sweep",
                    phase_lmuls=("m8", "m8", "m8"),
                    phase_totals=(128, 256, 128),
                    outer_iters=28,
                    hypothesis=db8_hypothesis,
                    extra_defines=("DB8_PRESSURE_REPEATS=2",),
                ),
                db_variant(
                    root=root,
                    source_name="db8",
                    name="dyn_m8_m2_m8",
                    define_value="DLB_VARIANT_DYN_M8_M2_M8",
                    kind="hysteresis_pressure_sweep",
                    phase_lmuls=("m8", "m2", "m8"),
                    phase_totals=(128, 256, 128),
                    outer_iters=28,
                    hypothesis=db8_hypothesis,
                    extra_defines=("DB8_PRESSURE_REPEATS=2",),
                ),
            ),
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
            case_name="db11",
            source_name="db11",
            variants=(
                db_variant(
                    root=root,
                    source_name="db11",
                    name="fixed_m1",
                    define_value="DLB_VARIANT_FIXED_M1",
                    kind="dependent_gamma_polynomial_m4_m2_m4",
                    phase_lmuls=("m1", "m1", "m1"),
                    phase_totals=(192, 192, 192),
                    outer_iters=34,
                    hypothesis=db11_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db11",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="dependent_gamma_polynomial_m4_m2_m4",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=34,
                    hypothesis=db11_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db11",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="dependent_gamma_polynomial_m4_m2_m4",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=34,
                    hypothesis=db11_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db11",
                    name="dyn_m4_m2_m4",
                    define_value="DLB_VARIANT_DYN_M4_M2_M4",
                    kind="dependent_gamma_polynomial_m4_m2_m4",
                    phase_lmuls=("m4", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=34,
                    hypothesis=db11_hypothesis,
                ),
            ),
        ),
        db_case(
            root=root,
            case_name="db12",
            source_name="db12",
            variants=(
                db_variant(
                    root=root,
                    source_name="db12",
                    name="fixed_m1",
                    define_value="DLB_VARIANT_FIXED_M1",
                    kind="dependent_normalized_force_m4_m2_m4",
                    phase_lmuls=("m1", "m1", "m1"),
                    phase_totals=(192, 192, 192),
                    outer_iters=24,
                    hypothesis=db12_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db12",
                    name="fixed_m2",
                    define_value="DLB_VARIANT_FIXED_M2",
                    kind="dependent_normalized_force_m4_m2_m4",
                    phase_lmuls=("m2", "m2", "m2"),
                    phase_totals=(192, 192, 192),
                    outer_iters=24,
                    hypothesis=db12_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db12",
                    name="fixed_m4",
                    define_value="DLB_VARIANT_FIXED_M4",
                    kind="dependent_normalized_force_m4_m2_m4",
                    phase_lmuls=("m4", "m4", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=24,
                    hypothesis=db12_hypothesis,
                ),
                db_variant(
                    root=root,
                    source_name="db12",
                    name="dyn_m4_m2_m4",
                    define_value="DLB_VARIANT_DYN_M4_M2_M4",
                    kind="dependent_normalized_force_m4_m2_m4",
                    phase_lmuls=("m4", "m2", "m4"),
                    phase_totals=(192, 192, 192),
                    outer_iters=24,
                    hypothesis=db12_hypothesis,
                ),
            ),
        ),
    )


def make_manifest() -> tuple[CaseSpec, ...]:
    return select_cases(make_catalog_manifest(), DEFAULT_CASE_NAMES, DEFAULT_SUITE)


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
