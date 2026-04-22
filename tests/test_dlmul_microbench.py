import sqlite3
import unittest
from unittest.mock import patch

from scripts import dlmul_microbench


class DlmulMicrobenchTest(unittest.TestCase):
    def test_iter_selected_jobs_filters_case_and_variant(self):
        manifest = dlmul_microbench.make_manifest()

        jobs = dlmul_microbench.iter_selected_jobs(
            manifest,
            {"mb4-two-phase"},
            {"m8_to_m1"},
        )

        self.assertEqual(len(jobs), 1)
        case, variant, sample_index = jobs[0]
        self.assertEqual(case.case_name, "mb4-two-phase")
        self.assertEqual(variant.name, "m8_to_m1")
        self.assertEqual(sample_index, 1)

    def test_manifest_uses_c_catalog_and_quick_suite(self):
        manifest = dlmul_microbench.make_manifest()
        jobs = dlmul_microbench.iter_selected_jobs(manifest, None, None)
        case_paths = {case.case_name: case.source_path for case in manifest}

        self.assertEqual(len(jobs), 17)
        self.assertTrue(case_paths["mb1-switch"].endswith("emulator/run/src/microbench/dlmul/mb1_switch.c"))
        self.assertTrue(case_paths["mb4-two-phase"].endswith("emulator/run/src/microbench/dlmul/mb4_two_phase.c"))

    def test_build_extra_cflags_disables_auto_vectorization(self):
        manifest = dlmul_microbench.make_manifest()
        variant = manifest[0].variants[0]

        flags = dlmul_microbench.build_extra_cflags(variant)

        self.assertIn("-fno-vectorize", flags)
        self.assertIn("-fno-slp-vectorize", flags)
        self.assertIn("-DMB1_FROM_VARIANT=1", flags)

    def test_ordered_patterns_match_reports_missing_pattern(self):
        matched, message = dlmul_microbench.ordered_patterns_match(
            "vsetvli zero, a0, e32, m4\n",
            (r"vsetvli.*m8", r"vsetvli.*m1"),
        )

        self.assertFalse(matched)
        self.assertIn("missing pattern", message)

    def test_create_table_contains_asm_validation_columns(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)

        dlmul_microbench.create_table(conn)
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(microbench_results)").fetchall()
        }

        self.assertEqual(columns["opt_ll_text"], "TEXT")
        self.assertEqual(columns["asm_text"], "TEXT")
        self.assertEqual(columns["asm_check_status"], "TEXT")
        self.assertEqual(columns["asm_expectation_json"], "TEXT")

    def test_make_row_from_emulate_result_warns_without_failing(self):
        case = next(case for case in dlmul_microbench.make_manifest() if case.case_name == "mb4-two-phase")
        variant = next(variant for variant in case.variants if variant.name == "m8_to_m1")
        result = {
            "summary": {
                "simulator_target": "xiangshan.KunminghuV2Config",
                "status": "PASS",
                "kernel_cycles": 123,
                "total_cycles": 456,
                "wall_time_s": 1.25,
                "sim_speed_khz": 4.5,
                "source": "/repo/emulator/run/src/microbench/dlmul/mb4_two_phase.c",
                "artifact_dir": "/repo/artifacts/emulate/dlmul",
                "container_log": "/repo/artifacts/emulate/dlmul/container.log",
                "run_detail_path": "/repo/artifacts/emulate/dlmul/log.txt",
                "trace_file": "/repo/artifacts/emulate/dlmul/trace.log",
                "docker_command": "docker run ...",
            },
            "container_log_text": "container",
            "run_detail": "detail",
            "opt_ll_text": "opt",
            "asm_text": "vsetvli zero, a0, e32, m8\nvsetvli zero, a0, e32, m8\n",
            "failed": False,
        }

        row = dlmul_microbench.make_row_from_emulate_result(
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
        case = next(case for case in dlmul_microbench.make_manifest() if case.case_name == "mb2-memory-phase")
        variant = next(variant for variant in case.variants if variant.name == "m4")

        with patch("scripts.dlmul_microbench.emulate.run_emulate_source", return_value={"summary": {}, "failed": False}) as mocked:
            dlmul_microbench.run_job(
                case=case,
                variant=variant,
                sample_index=1,
                image="example:latest",
                log_root="artifacts/microbench",
                timeout_s=120,
            )

        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["benchmark"], "dlmul_mb2_memory_phase__m4")
        self.assertTrue(kwargs["source"].endswith("emulator/run/src/microbench/dlmul/mb2_memory_phase.c"))
        self.assertEqual(kwargs["use_vf"], "")
        self.assertIn("-fno-vectorize", kwargs["extra_cflags"])


if __name__ == "__main__":
    unittest.main()
