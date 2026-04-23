import sqlite3
import unittest
from unittest.mock import patch

from scripts import dlmul_bench


class DlmulBenchTest(unittest.TestCase):
    def test_iter_selected_jobs_filters_case_and_variant(self):
        manifest = dlmul_bench.make_manifest()

        jobs = dlmul_bench.iter_selected_jobs(
            manifest,
            {"db1"},
            {"dyn_m4_m2_m4"},
        )

        self.assertEqual(len(jobs), 1)
        case, variant, sample_index = jobs[0]
        self.assertEqual(case.case_name, "db1")
        self.assertEqual(variant.name, "dyn_m4_m2_m4")
        self.assertEqual(sample_index, 1)

    def test_manifest_uses_c_catalog_and_db_suite(self):
        manifest = dlmul_bench.make_manifest()
        jobs = dlmul_bench.iter_selected_jobs(manifest, None, None)
        dyn_sources = {
            case.case_name: next(variant for variant in case.variants if variant.name.startswith("dyn_")).source_path
            for case in manifest
        }

        self.assertEqual(len(jobs), 25)
        self.assertTrue(dyn_sources["db1"].endswith("emulator/run/src/bench/dlmul/db1.c"))
        self.assertTrue(dyn_sources["db2"].endswith("emulator/run/src/bench/dlmul/db2.c"))
        self.assertTrue(dyn_sources["db3-long"].endswith("emulator/run/src/bench/dlmul/db3.c"))
        self.assertTrue(dyn_sources["db5"].endswith("emulator/run/src/bench/dlmul/db5.c"))

    def test_each_workload_has_expected_db_variants(self):
        manifest = dlmul_bench.make_manifest()

        self.assertEqual(
            [case.case_name for case in manifest],
            [
                "db1",
                "db2",
                "db3-short",
                "db3-medium",
                "db3-long",
                "db4",
                "db5",
            ],
        )
        self.assertEqual(
            [variant.name for variant in manifest[0].variants],
            ["fixed_m1", "fixed_m2", "fixed_m4", "dyn_m4_m2_m4"],
        )
        self.assertEqual(
            [variant.name for variant in manifest[1].variants],
            ["fixed_m2", "fixed_m4", "fixed_m8", "dyn_m8_m2_m8"],
        )
        self.assertEqual(
            [variant.name for variant in manifest[2].variants],
            ["fixed_m2", "fixed_m4", "dyn_m4_m2_m4"],
        )

    def test_build_extra_cflags_disables_auto_vectorization(self):
        manifest = dlmul_bench.make_manifest()
        variant = manifest[0].variants[0]

        flags = dlmul_bench.build_extra_cflags(variant)

        self.assertIn("-fno-vectorize", flags)
        self.assertIn("-fno-slp-vectorize", flags)
        self.assertIn("-DDLB_BENCH_VARIANT=", flags)

    def test_create_table_contains_expected_columns(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)

        dlmul_bench.create_table(conn)
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(dlmul_bench_results)").fetchall()
        }

        self.assertEqual(columns["opt_ll_text"], "TEXT")
        self.assertEqual(columns["asm_text"], "TEXT")
        self.assertEqual(columns["asm_check_status"], "TEXT")
        self.assertEqual(columns["asm_expectation_json"], "TEXT")

    def test_make_row_from_emulate_result_warns_without_failing(self):
        case = next(case for case in dlmul_bench.make_manifest() if case.case_name == "db1")
        variant = next(variant for variant in case.variants if variant.name == "dyn_m4_m2_m4")
        result = {
            "summary": {
                "simulator_target": "xiangshan.KunminghuV2Config",
                "status": "PASS",
                "kernel_cycles": 123,
                "total_cycles": 456,
                "wall_time_s": 1.25,
                "sim_speed_khz": 4.5,
                "source": "/repo/emulator/run/src/bench/dlmul/db1.c",
                "artifact_dir": "/repo/artifacts/dlmul-bench/db1",
                "container_log": "/repo/artifacts/dlmul-bench/db1/container.log",
                "run_detail_path": "/repo/artifacts/dlmul-bench/db1/log.txt",
                "trace_file": "/repo/artifacts/dlmul-bench/db1/trace.log",
                "docker_command": "docker run ...",
            },
            "container_log_text": "container",
            "run_detail": "detail",
            "opt_ll_text": "opt",
            "asm_text": "vsetvli zero, a0, e32, m4\nvsetvli zero, a0, e32, m4\n",
            "failed": False,
        }

        row = dlmul_bench.make_row_from_emulate_result(
            run_id="20260422150000",
            case=case,
            variant=variant,
            sample_index=1,
            result=result,
        )

        self.assertEqual(row["failure"], "")
        self.assertEqual(row["asm_check_status"], "WARN")
        self.assertIn("missing pattern", row["asm_check_message"])

    def test_run_job_delegates_to_emulate_source(self):
        case = next(case for case in dlmul_bench.make_manifest() if case.case_name == "db2")
        variant = next(variant for variant in case.variants if variant.name == "dyn_m8_m2_m8")

        with patch("scripts.dlmul_runner.emulate.run_emulate_source", return_value={"summary": {}, "failed": False}) as mocked:
            dlmul_bench.run_job(
                case=case,
                variant=variant,
                sample_index=1,
                image="example:latest",
                log_root="artifacts/dlmul-bench",
                timeout_s=120,
            )

        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["benchmark"], "dlmul_db2__dyn_m8_m2_m8")
        self.assertTrue(kwargs["source"].endswith("emulator/run/src/bench/dlmul/db2.c"))
        self.assertEqual(kwargs["use_vf"], "")
        self.assertIn("-fno-vectorize", kwargs["extra_cflags"])
        self.assertIn("-DDLB_BENCH_VARIANT=DLB_VARIANT_DYN_M8_M2_M8", kwargs["extra_cflags"])


if __name__ == "__main__":
    unittest.main()
