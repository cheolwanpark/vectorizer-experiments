import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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

    def test_manifest_uses_reduced_quick_suite(self):
        manifest = dlmul_microbench.make_manifest()
        jobs = dlmul_microbench.iter_selected_jobs(manifest, None, None)
        mb2 = next(case for case in manifest if case.case_name == "mb2-memory-phase")
        mb3 = next(case for case in manifest if case.case_name == "mb3-fractional-rescue")
        mb4 = next(case for case in manifest if case.case_name == "mb4-two-phase")

        self.assertEqual(len(jobs), 17)
        self.assertEqual([variant.name for variant in mb2.variants], ["m1", "m4", "m8"])
        self.assertEqual([variant.name for variant in mb3.variants], ["mf4_k8", "mf2_k8", "m1_k8", "m2_k8"])
        self.assertEqual(
            [variant.name for variant in mb4.variants],
            ["fixed_m1", "fixed_m4", "fixed_m8", "m8_to_m1", "m4_to_mf2"],
        )

    def test_build_inner_script_uses_assembly_only_flow(self):
        case = next(case for case in dlmul_microbench.make_manifest() if case.case_name == "mb1-switch")
        variant = next(variant for variant in case.variants if variant.name == "m1_to_m4")

        script = dlmul_microbench.build_inner_script(
            case=case,
            variant=variant,
            sample_index=1,
            timeout_s=120,
            target="xiangshan.KunminghuV2Config",
        )

        self.assertIn("crt_rv64.S", script)
        self.assertIn("entry.S", script)
        self.assertIn("mb1_switch.S", script)
        self.assertNotIn(".c ", script)
        self.assertNotIn("--use-vf", script)
        self.assertIn("python3 /workspace/emulator/run-sim.sh xiangshan.KunminghuV2Config", script)
        self.assertIn("--timeout=120", script)

    def test_resolve_timeout_promotes_xiangshan_legacy_default(self):
        self.assertEqual(
            dlmul_microbench.resolve_timeout(120, "xiangshan.KunminghuV2Config"),
            1800,
        )
        self.assertEqual(
            dlmul_microbench.resolve_timeout(300, "xiangshan.KunminghuV2Config"),
            300,
        )
        self.assertEqual(
            dlmul_microbench.resolve_timeout(120, "saturn.REFV512D128RocketConfig"),
            120,
        )

    def test_create_table_contains_dump_and_log_columns(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)

        dlmul_microbench.create_table(conn)
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(microbench_results)").fetchall()
        }

        self.assertEqual(columns["objdump_text"], "TEXT")
        self.assertEqual(columns["container_log_text"], "TEXT")
        self.assertEqual(columns["run_detail_text"], "TEXT")

    def test_entry_harness_matches_xiangshan_contract(self):
        entry = (
            Path(__file__).resolve().parents[1]
            / "emulator"
            / "benchmarks"
            / "microbenchmark"
            / "dlmul"
            / "common"
            / "entry.S"
        ).read_text(encoding="utf-8")

        self.assertIn('0x40600004', entry)
        self.assertIn('.asciz "KC="', entry)
        self.assertIn('.word 0x0000006b', entry)

    def test_run_job_records_dump_and_log_fields(self):
        case = next(case for case in dlmul_microbench.make_manifest() if case.case_name == "mb1-switch")
        variant = next(variant for variant in case.variants if variant.name == "m1_to_m4")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "emulator").mkdir()
            (root / "emulator" / "run-sim.sh").write_text("", encoding="utf-8")
            (root / "emulator" / "sim-configs.yaml").write_text("", encoding="utf-8")
            log_root = root / "artifacts" / "microbench"

            def fake_run(cmd, capture_output, text, check):
                self.assertIn("docker", cmd[0])
                mount_index = cmd.index("-v")
                while cmd[mount_index + 1].endswith(":ro"):
                    mount_index = cmd.index("-v", mount_index + 2)
                host_output_dir = Path(cmd[mount_index + 1].split(":", 1)[0])
                build_dir = host_output_dir / "build"
                logs_dir = host_output_dir / "logs"
                build_dir.mkdir(parents=True, exist_ok=True)
                logs_dir.mkdir(parents=True, exist_ok=True)
                elf = build_dir / "mb1-switch_m1_to_m4_s01.elf"
                objdump = build_dir / "mb1-switch_m1_to_m4_s01.objdump"
                log_file = logs_dir / "mb1-switch_m1_to_m4_s01.log"
                elf.write_text("elf", encoding="utf-8")
                objdump.write_text("objdump", encoding="utf-8")
                log_file.write_text("sim log", encoding="utf-8")

                stdout = "\n".join(
                    [
                        "Status:    PASS",
                        "Exit code: 0",
                        "Wall time: 1.25s",
                        "Kernel:    1,234 cycles",
                        "Total sim: 5,678 cycles",
                        "Sim speed: 4.5 kHz",
                        f"Log file:  {dlmul_microbench.CONTAINER_OUTPUT_ROOT / 'logs' / log_file.name}",
                        f"Trace:     {dlmul_microbench.CONTAINER_OUTPUT_ROOT / 'logs' / 'trace.log'}",
                    ]
                )
                return type("Completed", (), {"stdout": stdout, "stderr": "", "returncode": 0})()

            with patch("scripts.dlmul_microbench.subprocess.run", side_effect=fake_run):
                row = dlmul_microbench.run_job(
                    root=root,
                    run_id="20260422010101",
                    image="example:latest",
                    log_root=log_root,
                    case=case,
                    variant=variant,
                    sample_index=1,
                    timeout_s=120,
                    target="xiangshan.KunminghuV2Config",
                )

        self.assertEqual(row["failure"], "")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["kernel_cycles"], 1234)
        self.assertEqual(row["total_cycles"], 5678)
        self.assertEqual(row["objdump_text"], "objdump")
        self.assertEqual(row["run_detail_text"], "sim log")


if __name__ == "__main__":
    unittest.main()
