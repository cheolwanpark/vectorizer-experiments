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


DEFAULT_DB_PATH = "artifacts/microbench.sqlite"
DEFAULT_LOG_ROOT = "artifacts/microbench"
DEFAULT_CONCURRENCY = dlmul_runner.DEFAULT_CONCURRENCY
DEFAULT_TIMEOUT = dlmul_runner.DEFAULT_TIMEOUT
DEFAULT_LEN_1D = dlmul_runner.DEFAULT_LEN_1D
DEFAULT_LMUL = dlmul_runner.DEFAULT_LMUL
CATALOG_ROOT = Path("emulator") / "run" / "src" / "microbench" / "dlmul"


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


def create_table(conn: sqlite3.Connection) -> None:
    dlmul_runner.create_table(conn, "microbench_results")


def make_manifest() -> tuple[CaseSpec, ...]:
    root = CATALOG_ROOT

    lmul_variants_wide = (
        ("mf2", 102),
        ("m1", 1),
        ("m2", 2),
        ("m4", 4),
    )

    mb1_variants = (
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
    )

    mb2_variants = tuple(
        VariantSpec(
            name=lmul_name,
            defines=(f"MB2_VARIANT={lmul_value}", "MB2_TOTAL_ELEMS=256", "MB2_OUTER_ITERS=64"),
            params={"kind": "memory_phase", "lmul": lmul_name, "total_elems": 256, "outer_iters": 64, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b",),
        )
        for lmul_name, lmul_value in (("m1", 1), ("m4", 4), ("m8", 8))
    )

    mb3_variants = tuple(
        VariantSpec(
            name=f"{lmul_name}_k8",
            defines=(f"MB3_VARIANT={lmul_value}", "MB3_TEMP_COUNT=8", "MB3_TOTAL_ELEMS=64", "MB3_OUTER_ITERS=48"),
            params={"kind": "fractional_rescue", "lmul": lmul_name, "temp_reg_count": 8, "total_elems": 64, "outer_iters": 48, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b",),
        )
        for lmul_name, lmul_value in (("mf2", 102), ("m1", 1), ("m2", 2))
    )

    mb4_variants = (
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
    )

    mb5_variants = tuple(
        VariantSpec(
            name=f"{lmul_name}_acc{accs}",
            defines=(f"MB5_LMUL_VARIANT={lmul_value}", f"MB5_ACC_COUNT={accs}", "MB5_TOTAL_ELEMS=64", "MB5_OUTER_ITERS=32"),
            params={"kind": "widening_cliff", "lmul": lmul_name, "accumulators": accs, "total_elems": 64, "outer_iters": 32, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e16,\s*{lmul_name}\b", r"vw"),
        )
        for lmul_name, lmul_value in lmul_variants_wide
        for accs in (2, 4, 8)
    )

    mb6_shapes = (
        ("copy_1load", 1, (r"vle32", r"vse32")),
        ("saxpy_1load", 2, (r"vfmul|vfmacc", r"vse32")),
        ("triad_2load", 3, (r"vle32", r"vfadd", r"vse32")),
        ("axpy_2load", 4, (r"vle32", r"vfmul|vfmacc", r"vse32")),
    )
    mb6_variants = tuple(
        VariantSpec(
            name=f"{shape_name}__{lmul_name}",
            defines=(f"MB6_SHAPE={shape_id}", f"MB6_LMUL_VARIANT={lmul_value}", "MB6_TOTAL_ELEMS=256", "MB6_OUTER_ITERS=32"),
            params={"kind": "stream_count_sweep", "shape": shape_name, "lmul": lmul_name, "total_elems": 256, "outer_iters": 32, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b", *shape_patterns),
        )
        for shape_name, shape_id, shape_patterns in mb6_shapes
        for lmul_name, lmul_value in (("m1", 1), ("m4", 4), ("m8", 8))
    )

    mb7_ops = (
        ("add_chain", 1, (r"vfadd",)),
        ("fma_chain", 2, (r"vfmacc|vfmadd",)),
    )
    mb7_variants = tuple(
        VariantSpec(
            name=f"{op_name}__{lmul_name}",
            defines=(f"MB7_OP={op_id}", f"MB7_LMUL_VARIANT={lmul_value}", "MB7_TOTAL_ELEMS=128", "MB7_CHAIN_DEPTH=32", "MB7_OUTER_ITERS=16"),
            params={"kind": "pure_compute", "op": op_name, "lmul": lmul_name, "total_elems": 128, "chain_depth": 32, "outer_iters": 16, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b", *op_patterns),
        )
        for op_name, op_id, op_patterns in mb7_ops
        for lmul_name, lmul_value in (("m1", 1), ("m2", 2), ("m4", 4), ("m8", 8))
    )

    mb8_classes = (
        ("plain_alu", 1, (r"vfadd",)),
        ("fma", 2, (r"vfmacc|vfmadd",)),
        ("widening", 3, (r"vw",)),
    )
    mb8_variants = tuple(
        VariantSpec(
            name=f"{class_name}__{lmul_name}__k{k}",
            defines=(f"MB8_CLASS={class_id}", f"MB8_LMUL_VARIANT={lmul_value}", f"MB8_K={k}", "MB8_TOTAL_ELEMS=64", "MB8_OUTER_ITERS=24"),
            params={"kind": "live_temporary_sweep", "op_class": class_name, "lmul": lmul_name, "k": k, "total_elems": 64, "outer_iters": 24, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e{16 if class_name == 'widening' else 32},\s*{lmul_name}\b", *class_patterns),
        )
        for class_name, class_id, class_patterns in mb8_classes
        for lmul_name, lmul_value in (("mf2", 102), ("m1", 1), ("m2", 2), ("m4", 4))
        for k in (4, 8, 12)
    )

    mb9_lengths = (
        ("short", 1, 32, 16),
        ("medium", 2, 128, 64),
        ("long", 3, 256, 128),
    )
    mb9_patterns = (
        ("m8_to_m1", 1, "m8", "m1", 8, 1),
        ("m4_to_mf2", 2, "m4", "mf2", 4, 102),
    )
    mb9_variants = tuple(
        VariantSpec(
            name=f"{pattern_name}__{length_name}",
            defines=(f"MB9_PATTERN={pattern_id}", f"MB9_LENGTH={length_id}", f"MB9_PHASE1_TOTAL_ELEMS={phase1_elems}", f"MB9_PHASE2_TOTAL_ELEMS={phase2_elems}", "MB9_OUTER_ITERS=24"),
            params={"kind": "phase_length_sweep", "pattern": pattern_name, "length": length_name, "phase1_total_elems": phase1_elems, "phase2_total_elems": phase2_elems, "outer_iters": 24, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{phase1_lmul}\b", rf"vsetvli.*e32,\s*{phase2_lmul}\b", rf"vsetvli.*e32,\s*{phase1_lmul}\b"),
        )
        for pattern_name, pattern_id, phase1_lmul, phase2_lmul, _, _ in mb9_patterns
        for length_name, length_id, phase1_elems, phase2_elems in mb9_lengths
    )

    mb10_levels = (
        ("light", 1),
        ("medium", 2),
        ("heavy", 3),
    )
    mb10_variants = tuple(
        VariantSpec(
            name=f"{lmul_name}_{level_name}",
            defines=(f"MB10_LMUL_VARIANT={lmul_value}", f"MB10_TRAFFIC_LEVEL={level_id}", "MB10_TOTAL_ELEMS=128", "MB10_OUTER_ITERS=24"),
            params={"kind": "spill_surrogate", "lmul": lmul_name, "traffic": level_name, "total_elems": 128, "outer_iters": 24, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b", r"vle32", r"vse32"),
        )
        for lmul_name, lmul_value in (("m1", 1), ("m2", 2), ("m4", 4))
        for level_name, level_id in mb10_levels
    )

    mb11_densities = (
        ("sparse", 1),
        ("balanced", 2),
        ("dense", 3),
    )
    mb11_variants = tuple(
        VariantSpec(
            name=f"{lmul_name}_{density_name}",
            defines=(f"MB11_LMUL_VARIANT={lmul_value}", f"MB11_DENSITY={density_id}", "MB11_TOTAL_ELEMS=128", "MB11_OUTER_ITERS=24"),
            params={"kind": "masked_execution", "lmul": lmul_name, "density": density_name, "total_elems": 128, "outer_iters": 24, "len_1d": 256},
            asm_patterns=(rf"vsetvli.*e32,\s*{lmul_name}\b", r"vm", r"v0\.t"),
        )
        for lmul_name, lmul_value in (("m1", 1), ("m4", 4), ("m8", 8))
        for density_name, density_id in mb11_densities
    )

    return (
        CaseSpec("dynamic_lmul", "mb1-switch", str(root / "mb1_switch.c"), mb1_variants),
        CaseSpec("dynamic_lmul", "mb2-memory-phase", str(root / "mb2_memory_phase.c"), mb2_variants),
        CaseSpec("dynamic_lmul", "mb3-fractional-rescue", str(root / "mb3_fractional_rescue.c"), mb3_variants),
        CaseSpec("dynamic_lmul", "mb4-two-phase", str(root / "mb4_two_phase.c"), mb4_variants),
        CaseSpec("dynamic_lmul", "mb5-widening-cliff", str(root / "mb5_widening_cliff.c"), mb5_variants),
        CaseSpec("dynamic_lmul", "mb6-stream-count-sweep", str(root / "mb6_stream_count_sweep.c"), mb6_variants),
        CaseSpec("dynamic_lmul", "mb7-pure-compute", str(root / "mb7_pure_compute.c"), mb7_variants),
        CaseSpec("dynamic_lmul", "mb8-live-temporary-sweep", str(root / "mb8_live_temporary_sweep.c"), mb8_variants),
        CaseSpec("dynamic_lmul", "mb9-phase-length-sweep", str(root / "mb9_phase_length_sweep.c"), mb9_variants),
        CaseSpec("dynamic_lmul", "mb10-spill-surrogate", str(root / "mb10_spill_surrogate.c"), mb10_variants),
        CaseSpec("dynamic_lmul", "mb11-masked-execution", str(root / "mb11_masked_execution.c"), mb11_variants),
    )


def main() -> None:
    args = parse_args()
    dlmul_runner.run_suite(
        args=args,
        manifest=make_manifest(),
        table_name="microbench_results",
        suite_label="dlmul-microbench",
    )


if __name__ == "__main__":
    main()
