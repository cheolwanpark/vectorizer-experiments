import argparse
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import emulate_all


def create_vfs_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE vfs (
            bench TEXT NOT NULL,
            use_vf TEXT NOT NULL,
            raw_vf TEXT NOT NULL,
            cost TEXT NOT NULL,
            compare TEXT NOT NULL,
            plan_index INTEGER,
            selected INTEGER NOT NULL,
            failure TEXT NOT NULL,
            failure_message TEXT NOT NULL,
            source TEXT NOT NULL,
            vplan_log_path TEXT NOT NULL,
            vplan_log_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


class EmulateAllTest(unittest.TestCase):
    def test_parse_args_defaults_to_concurrency_five_without_samples(self):
        with patch("sys.argv", ["emulate_all.py"]):
            args = emulate_all.parse_args()

        self.assertEqual(args.concurrency, 5)
        self.assertEqual(args.vfs_db_dir, "artifacts/vfs")
        self.assertEqual(args.vfs_db, "artifacts/vfs.db")
        self.assertFalse(hasattr(args, "samples"))

    def test_load_vfs_data_splits_candidates_and_failures(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vfs.sqlite"
            conn = sqlite3.connect(db_path)
            create_vfs_table(conn)
            conn.executemany(
                """
                INSERT INTO vfs (
                    bench, use_vf, raw_vf, cost, compare, plan_index, selected,
                    failure, failure_message, source, vplan_log_path, vplan_log_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "s000",
                        "fixed:2",
                        "2",
                        "24",
                        "1200",
                        0,
                        0,
                        "",
                        "",
                        "manual",
                        "/tmp/s000.log",
                        "log0",
                        "2026-04-02T00:00:00",
                    ),
                    (
                        "s000",
                        "fixed:4",
                        "4",
                        "12",
                        "600",
                        0,
                        1,
                        "",
                        "",
                        "manual",
                        "/tmp/s000.log",
                        "log0",
                        "2026-04-02T00:00:00",
                    ),
                    (
                        "s001",
                        "",
                        "",
                        "",
                        "",
                        None,
                        0,
                        "no_vf",
                        "no parseable VF entries found in vplan-explain output",
                        "manual",
                        "/tmp/s001.log",
                        "log1",
                        "2026-04-02T00:00:00",
                    ),
                ],
            )
            conn.commit()
            conn.close()

            candidates_by_bench, failures_by_bench = emulate_all.load_vfs_data(db_path)

        self.assertEqual([row["use_vf"] for row in candidates_by_bench["s000"]], ["fixed:2", "fixed:4"])
        self.assertEqual(failures_by_bench["s001"]["failure"], "no_vf")
        self.assertEqual(failures_by_bench["s001"]["vplan_log_text"], "log1")

    def test_make_default_vplan_result_returns_empty_metadata(self):
        result = emulate_all.make_default_vplan_result()

        self.assertEqual(
            result,
            {
                "source": "",
                "vplan_log": "",
                "vplan_log_text": "",
                "container_log_text": "",
            },
        )

    def test_create_table_uses_artifact_columns_without_sample_index(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)

        emulate_all.create_table(conn)
        columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(emulate_results)").fetchall()
        }

        self.assertNotIn("sample_index", columns)
        self.assertEqual(columns["opt_ll_text"], "VARCHAR")
        self.assertEqual(columns["asm_text"], "VARCHAR")

    def test_make_emulate_row_copies_artifact_texts(self):
        args = argparse.Namespace(image="img", len_1d=4096, lmul=1, timeout=120)
        vplan_result = {"vplan_log": "/tmp/vplan.log", "vplan_log_text": "vplan"}
        emulate_result = {
            "summary": {"status": "PASS", "kernel_cycles": 10, "total_cycles": 20},
            "container_log_text": "container",
            "run_detail": "run",
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

        self.assertEqual(row["opt_ll_text"], "opt")
        self.assertEqual(row["asm_text"], "asm")

    def test_find_missing_artifacts_reports_empty_fields(self):
        missing = emulate_all.find_missing_artifacts(
            {
                "opt_ll_text": "opt",
                "asm_text": "",
            },
            "fixed:4",
        )

        self.assertEqual(missing, ["asm_text"])

    def test_find_missing_artifacts_requires_default_run_artifacts(self):
        missing = emulate_all.find_missing_artifacts(
            {
                "opt_ll_text": "",
                "asm_text": "",
            },
            "",
        )

        self.assertEqual(missing, ["opt_ll_text", "asm_text"])

    def test_main_records_vplan_failure_and_still_runs_baseline(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts_dir = root / "artifacts"
            artifacts_dir.mkdir()
            vfs_db = artifacts_dir / "vfs.db"
            conn = sqlite3.connect(vfs_db)
            create_vfs_table(conn)
            conn.execute(
                """
                INSERT INTO vfs (
                    bench, use_vf, raw_vf, cost, compare, plan_index, selected,
                    failure, failure_message, source, vplan_log_path, vplan_log_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "s000",
                    "",
                    "",
                    "",
                    "",
                    None,
                    0,
                    "no_vf",
                    "no parseable VF entries found in vplan-explain output",
                    "manual",
                    "/tmp/s000.log",
                    "vplan log",
                    "2026-04-02T00:00:00",
                ),
            )
            conn.commit()
            conn.close()

            fake_emulate_result = {
                "summary": {"status": "PASS", "kernel_cycles": 10, "total_cycles": 20},
                "container_log_text": "container",
                "run_detail": "run",
                "opt_ll_text": "opt",
                "asm_text": "asm",
                "failed": False,
            }

            with patch("sys.argv", ["emulate_all.py", "--db-dir", str(artifacts_dir), "--vfs-db", str(vfs_db)]):
                with patch.object(emulate_all.emulate, "repo_root", return_value=root):
                    with patch.object(emulate_all, "discover_benches", return_value=["s000"]):
                        with patch.object(emulate_all.emulate, "ensure_image_exists"):
                            with patch.object(emulate_all, "run_emulate_job", return_value=fake_emulate_result):
                                emulate_all.main()

            per_workload_dbs = list(artifacts_dir.glob("emulate-result-s000-*.sqlite"))
            aggregate_dbs = [
                path
                for path in artifacts_dir.glob("emulate-result-*.sqlite")
                if path not in per_workload_dbs
            ]
            self.assertEqual(len(per_workload_dbs), 1)
            self.assertEqual(len(aggregate_dbs), 1)
            result_conn = sqlite3.connect(per_workload_dbs[0])
            rows = result_conn.execute(
                "SELECT stage, bench, use_vf, failure, failure_message, status, vplan_log_text "
                "FROM emulate_results ORDER BY stage, use_vf"
            ).fetchall()
            result_conn.close()

        self.assertEqual(
            rows,
            [
                ("emulate", "s000", "", "", "", "PASS", ""),
                (
                    "vplan",
                    "s000",
                    "",
                    "no_vf",
                    "no parseable VF entries found in vplan-explain output",
                    "SKIP",
                    "vplan log",
                ),
            ],
        )

    def test_main_uses_vfs_db_without_running_vplan_explain(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts_dir = root / "artifacts"
            artifacts_dir.mkdir()
            vfs_db = artifacts_dir / "vfs.db"
            conn = sqlite3.connect(vfs_db)
            create_vfs_table(conn)
            conn.execute(
                """
                INSERT INTO vfs (
                    bench, use_vf, raw_vf, cost, compare, plan_index, selected,
                    failure, failure_message, source, vplan_log_path, vplan_log_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "s000",
                    "fixed:4",
                    "4",
                    "12",
                    "600",
                    0,
                    1,
                    "",
                    "",
                    "manual",
                    "/tmp/s000.log",
                    "vplan log",
                    "2026-04-02T00:00:00",
                ),
            )
            conn.commit()
            conn.close()

            fake_emulate_result = {
                "summary": {"status": "PASS", "kernel_cycles": 10, "total_cycles": 20},
                "container_log_text": "container",
                "run_detail": "run",
                "opt_ll_text": "opt",
                "asm_text": "asm",
                "failed": False,
            }

            with patch("sys.argv", ["emulate_all.py", "--db-dir", str(artifacts_dir), "--vfs-db", str(vfs_db)]):
                with patch.object(emulate_all.emulate, "repo_root", return_value=root):
                    with patch.object(emulate_all, "discover_benches", return_value=["s000"]):
                        with patch.object(emulate_all.emulate, "ensure_image_exists"):
                            with patch.object(emulate_all, "run_emulate_job", return_value=fake_emulate_result):
                                with patch.object(
                                    emulate_all.vplan_explain,
                                    "run_vplan_explain",
                                    side_effect=AssertionError("vplan-explain should not run"),
                                ) as vplan_mock:
                                    emulate_all.main()

            self.assertFalse(vplan_mock.called)
            per_workload_dbs = list(artifacts_dir.glob("emulate-result-s000-*.sqlite"))
            aggregate_dbs = [
                path
                for path in artifacts_dir.glob("emulate-result-*.sqlite")
                if path not in per_workload_dbs
            ]
            self.assertEqual(len(per_workload_dbs), 1)
            self.assertEqual(len(aggregate_dbs), 1)
            result_conn = sqlite3.connect(per_workload_dbs[0])
            rows = result_conn.execute(
                "SELECT stage, bench, use_vf, failure, kernel_cycles, vplan_log_text "
                "FROM emulate_results ORDER BY use_vf"
            ).fetchall()
            result_conn.close()

        self.assertEqual(
            rows,
            [
                ("emulate", "s000", "", "", 10, ""),
                ("emulate", "s000", "fixed:4", "", 10, "vplan log"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
