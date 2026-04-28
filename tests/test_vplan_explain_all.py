import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import benchmark_sources, vplan_explain_all


class VPlanExplainAllTest(unittest.TestCase):
    def test_write_workload_db_records_structured_unsupported_analysis(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vfs-multi.sqlite"
            row_count, status = vplan_explain_all.write_workload_db(
                db_path,
                {
                    "bench": "multi",
                    "exit_code": 0,
                    "vf_candidates": [],
                    "analysis_failure": "unsupported_analysis_source",
                    "analysis_failure_message": "multiple C sources",
                    "source": "emulator/run/src/multi/manifest.yaml",
                    "vplan_log": "",
                    "vplan_log_text": "",
                    "container_log_text": "",
                },
            )

            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT bench, failure, failure_message FROM vfs"
            ).fetchall()
            conn.close()

        self.assertEqual(row_count, 1)
        self.assertEqual(status, "unsupported")
        self.assertEqual(rows, [("multi", "unsupported_analysis_source", "multiple C sources")])

    def test_main_writes_per_workload_and_aggregate_dbs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload = benchmark_sources.CatalogWorkload(
                workload_id="npb_is_s",
                kind="manifest",
            )

            with patch(
                "sys.argv",
                [
                    "vplan_explain_all.py",
                    "--db-dir",
                    "artifacts/vfs",
                    "--compat-db-path",
                    "artifacts/vfs.db",
                ],
            ):
                with patch.object(vplan_explain_all.emulate, "repo_root", return_value=root):
                    with patch.object(vplan_explain_all, "discover_workloads", return_value=[workload]):
                        with patch.object(vplan_explain_all.vplan_explain, "ensure_image_exists"):
                            with patch.object(
                                vplan_explain_all.vplan_explain,
                                "run_vplan_explain",
                                return_value={
                                    "bench": "npb_is_s",
                                    "exit_code": 0,
                                    "vf_candidates": [
                                        {
                                            "use_vf": "fixed:4",
                                            "raw_vf": "4",
                                            "cost": "12",
                                            "compare": "600",
                                            "plan_index": 0,
                                            "selected": True,
                                        }
                                    ],
                                    "source": "emulator/run/src/npb/npb_is_s/is.c",
                                    "vplan_log": "/tmp/npb.log",
                                    "vplan_log_text": "log",
                                    "container_log_text": "",
                                    "analysis_failure": "",
                                    "analysis_failure_message": "",
                                },
                            ):
                                vplan_explain_all.main()

            per_workload_db = root / "artifacts" / "vfs" / "vfs-npb_is_s.sqlite"
            aggregate_dbs = list(root.glob("artifacts/vfs-rvv-all-*.sqlite"))
            compat_db = root / "artifacts" / "vfs.db"
            self.assertTrue(per_workload_db.exists())
            self.assertEqual(len(aggregate_dbs), 1)
            self.assertTrue(compat_db.exists())

            conn = sqlite3.connect(per_workload_db)
            rows = conn.execute(
                "SELECT bench, use_vf, compare FROM vfs"
            ).fetchall()
            conn.close()

        self.assertEqual(rows, [("npb_is_s", "fixed:4", "600")])

    def test_main_passes_catalog_dir_filter(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload = benchmark_sources.CatalogWorkload(workload_id="npb_is_s", kind="manifest")

            with patch("sys.argv", ["vplan_explain_all.py", "--catalog-dir", "npb"]):
                with patch.object(vplan_explain_all.emulate, "repo_root", return_value=root):
                    with patch.object(vplan_explain_all, "discover_workloads", return_value=[workload]) as discover_mock:
                        with patch.object(vplan_explain_all.vplan_explain, "ensure_image_exists"):
                            with patch.object(
                                vplan_explain_all.vplan_explain,
                                "run_vplan_explain",
                                return_value={
                                    "bench": "npb_is_s",
                                    "exit_code": 0,
                                    "vf_candidates": [],
                                    "source": "",
                                    "vplan_log": "",
                                    "vplan_log_text": "",
                                    "container_log_text": "",
                                    "analysis_failure": "unsupported_analysis_source",
                                    "analysis_failure_message": "no C source",
                                },
                            ):
                                vplan_explain_all.main()

        self.assertEqual(discover_mock.call_args.args[1], "npb")


if __name__ == "__main__":
    unittest.main()
