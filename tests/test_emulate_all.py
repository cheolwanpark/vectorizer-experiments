import argparse
import sqlite3
import unittest
from unittest.mock import patch

from scripts import emulate_all


class EmulateAllTest(unittest.TestCase):
    def test_parse_args_defaults_to_concurrency_five_without_samples(self):
        with patch("sys.argv", ["emulate_all.py"]):
            args = emulate_all.parse_args()

        self.assertEqual(args.concurrency, 5)
        self.assertFalse(hasattr(args, "samples"))

    def test_create_table_uses_artifact_columns_without_sample_index(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)

        emulate_all.create_table(conn)
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(emulate_results)").fetchall()
        }

        self.assertNotIn("sample_index", columns)
        self.assertEqual(columns["raw_ll_text"], "VARCHAR")
        self.assertEqual(columns["prevec_ll_text"], "VARCHAR")
        self.assertEqual(columns["opt_ll_text"], "VARCHAR")
        self.assertEqual(columns["asm_text"], "VARCHAR")

    def test_make_emulate_row_copies_artifact_texts(self):
        args = argparse.Namespace(image="img", len_1d=4096, lmul=1, timeout=120)
        vplan_result = {"vplan_log": "/tmp/vplan.log", "vplan_log_text": "vplan"}
        emulate_result = {
            "summary": {"status": "PASS", "kernel_cycles": 10, "total_cycles": 20},
            "container_log_text": "container",
            "run_log_text": "run",
            "raw_ll_text": "raw",
            "prevec_ll_text": "prevec",
            "opt_ll_text": "opt",
            "asm_text": "asm",
            "failed": False,
        }

        row = emulate_all.make_emulate_row(
            run_id="run",
            bench="s000",
            use_vf="fixed:4",
            args=args,
            vplan_result=vplan_result,
            emulate_result=emulate_result,
        )

        self.assertEqual(row["raw_ll_text"], "raw")
        self.assertEqual(row["prevec_ll_text"], "prevec")
        self.assertEqual(row["opt_ll_text"], "opt")
        self.assertEqual(row["asm_text"], "asm")

    def test_find_missing_artifacts_reports_empty_fields(self):
        missing = emulate_all.find_missing_artifacts(
            {
                "raw_ll_text": "raw",
                "prevec_ll_text": "",
                "opt_ll_text": "opt",
                "asm_text": "",
            }
        )

        self.assertEqual(missing, ["prevec_ll_text", "asm_text"])


if __name__ == "__main__":
    unittest.main()
