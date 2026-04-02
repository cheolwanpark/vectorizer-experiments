import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.plot_results import (
    BenchMetricSummary,
    EmulateAggregate,
    MetricPoint,
    ReportData,
    VFCandidate,
    build_metric_summaries,
    build_top_n_overlap_distributions,
    load_emulate_data,
    load_vfs_data,
    parse_effective_cost,
    parse_vf_factor,
    render_html,
)


class PlotResultsTest(unittest.TestCase):
    def test_parse_vf_factor(self):
        self.assertEqual(parse_vf_factor("fixed:4"), 4)
        self.assertEqual(parse_vf_factor("scalable:2"), 2)
        self.assertIsNone(parse_vf_factor("fixed:0"))
        self.assertIsNone(parse_vf_factor("weird"))

    def test_parse_effective_cost_divides_by_vf(self):
        self.assertEqual(parse_effective_cost("24", "fixed:4"), 6.0)
        self.assertEqual(parse_effective_cost("24", "scalable:2"), 12.0)
        self.assertIsNone(parse_effective_cost("", "fixed:4"))
        self.assertIsNone(parse_effective_cost("24", "unknown"))

    def test_build_metric_summaries_ranks_by_compare(self):
        candidates = {
            ("bench", "fixed:2"): VFCandidate(
                bench="bench",
                use_vf="fixed:2",
                raw_vf="2",
                raw_cost="24",
                raw_compare="3500",
                compare=3500.0,
                selected=False,
            ),
            ("bench", "fixed:4"): VFCandidate(
                bench="bench",
                use_vf="fixed:4",
                raw_vf="4",
                raw_cost="32",
                raw_compare="1750",
                compare=1750.0,
                selected=True,
            ),
        }
        aggregates = {
            ("bench", "fixed:2"): EmulateAggregate(
                bench="bench", use_vf="fixed:2", kernel_samples=[13.0], total_samples=[13.0]
            ),
            ("bench", "fixed:4"): EmulateAggregate(
                bench="bench", use_vf="fixed:4", kernel_samples=[10.0], total_samples=[10.0]
            ),
        }

        summaries = build_metric_summaries("kernel_cycles", candidates, aggregates)

        self.assertEqual(len(summaries), 1)
        summary: BenchMetricSummary = summaries[0]
        point_by_vf = {point.use_vf: point for point in summary.points}
        self.assertEqual(point_by_vf["fixed:2"].compare, 3500.0)
        self.assertEqual(point_by_vf["fixed:4"].compare, 1750.0)
        self.assertEqual(summary.compare_best_vf, "fixed:4")

    def test_build_top_n_overlap_distributions_uses_overlap_ratio(self):
        def make_candidates(bench, rows, selected_vf):
            candidates = {}
            for use_vf, raw_compare in rows:
                candidates[(bench, use_vf)] = VFCandidate(
                    bench=bench,
                    use_vf=use_vf,
                    raw_vf=use_vf.split(":", 1)[1],
                    raw_cost="",
                    raw_compare=str(raw_compare),
                    compare=float(raw_compare),
                    selected=(use_vf == selected_vf),
                )
            return candidates

        candidates = {}
        candidates.update(
            make_candidates(
                "bench-a",
                [("fixed:1", 10), ("fixed:2", 30), ("fixed:4", 80)],
                "fixed:1",
            )
        )
        candidates.update(
            make_candidates(
                "bench-b",
                [("fixed:1", 10), ("fixed:2", 30), ("fixed:4", 80)],
                "fixed:1",
            )
        )
        aggregates = {
            ("bench-a", "fixed:1"): EmulateAggregate("bench-a", "fixed:1", [1.0], [1.0]),
            ("bench-a", "fixed:2"): EmulateAggregate("bench-a", "fixed:2", [3.0], [3.0]),
            ("bench-a", "fixed:4"): EmulateAggregate("bench-a", "fixed:4", [2.0], [2.0]),
            ("bench-b", "fixed:1"): EmulateAggregate("bench-b", "fixed:1", [1.0], [1.0]),
            ("bench-b", "fixed:2"): EmulateAggregate("bench-b", "fixed:2", [2.0], [2.0]),
            ("bench-b", "fixed:4"): EmulateAggregate("bench-b", "fixed:4", [3.0], [3.0]),
        }

        summaries = build_metric_summaries("kernel_cycles", candidates, aggregates)
        ns, distributions, eligible = build_top_n_overlap_distributions(summaries)

        self.assertEqual(ns, [1, 2, 3])
        self.assertEqual(eligible, [2, 2, 2])
        self.assertEqual(distributions[0], [1.0, 1.0])
        self.assertEqual(distributions[1], [0.5, 1.0])
        self.assertEqual(distributions[2], [1.0, 1.0])

    def test_render_html_swaps_removed_sections_for_selector_and_quality_overview(self):
        summary = BenchMetricSummary(
            bench="s000",
            metric_name="kernel_cycles",
            points=[
                MetricPoint(
                    bench="s000",
                    use_vf="fixed:2",
                    selected=True,
                    raw_cost="24",
                    raw_compare="3500",
                    compare=3500.0,
                    samples=[10.0],
                    median_value=10.0,
                    min_value=10.0,
                    max_value=10.0,
                    n_success=1,
                    compare_rank=1,
                    actual_rank=1,
                )
            ],
            selected_vf="fixed:2",
            compare_best_vf="fixed:2",
            actual_best_vf="fixed:2",
            max_abs_rank_delta=0,
            selected_rank_delta=0,
            spearman=1.0,
        )
        data = ReportData(
            vfs_db=Path("artifacts/vfs.db"),
            emulate_db=Path("artifacts/emulate.sqlite"),
            benches=["s000", "s001"],
            candidates={},
            candidate_counts={"s000": 1},
            vplan_failures=[],
            emulate_aggregates={},
            emulate_failure_counts={},
            metric_summaries={"kernel_cycles": [summary], "total_cycles": []},
        )
        plots = {
            "coverage": "coverage.png",
            "scatter:kernel_cycles": "scatter-kernel.png",
            "scatter:total_cycles": "scatter-total.png",
            "ranking_quality": "ranking-quality.png",
            "detail:s000": "detail-s000.png",
        }

        html = render_html(data, plots)

        self.assertIn("Ranking quality overview", html)
        self.assertIn("bench-search", html)
        self.assertIn("bench-select", html)
        self.assertIn("Bench detail: s000", html)
        self.assertNotIn("Bench detail: s001", html)
        self.assertNotIn("<option value='s001'>", html)
        self.assertNotIn("Best ratio heatmap", html)
        self.assertNotIn("Rank delta heatmap", html)
        self.assertNotIn("Top mismatch benches", html)

    def test_load_emulate_data_reads_schema_without_sample_index(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "emulate.sqlite"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE emulate_results (
                    stage TEXT NOT NULL,
                    failure TEXT NOT NULL,
                    bench TEXT NOT NULL,
                    use_vf TEXT NOT NULL,
                    kernel_cycles INTEGER,
                    total_cycles INTEGER
                )
                """
            )
            conn.execute(
                """
                INSERT INTO emulate_results (
                    stage, failure, bench, use_vf, kernel_cycles, total_cycles
                ) VALUES ('emulate', '', 's000', 'fixed:4', 10, 20)
                """
            )
            conn.commit()
            conn.close()

            aggregates, failure_counts = load_emulate_data(db_path, set())

        self.assertEqual(failure_counts, {})
        self.assertEqual(aggregates[("s000", "fixed:4")].kernel_samples, [10.0])
        self.assertEqual(aggregates[("s000", "fixed:4")].total_samples, [20.0])

    def test_load_vfs_data_prefers_compare_column(self):
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "vfs.sqlite"
            conn = sqlite3.connect(db_path)
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
            conn.execute(
                """
                INSERT INTO vfs (
                    bench, use_vf, raw_vf, cost, compare, plan_index, selected,
                    failure, failure_message, source, vplan_log_path, vplan_log_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("s000", "fixed:4", "4", "7", "1750", 1, 1, "", "", "", "", "", "2026-04-02T00:00:00"),
            )
            conn.commit()
            conn.close()

            candidates, candidate_counts, failures = load_vfs_data(db_path, set())

        self.assertEqual(candidate_counts, {"s000": 1})
        self.assertEqual(failures, [])
        self.assertEqual(candidates[("s000", "fixed:4")].raw_cost, "7")
        self.assertEqual(candidates[("s000", "fixed:4")].raw_compare, "1750")
        self.assertEqual(candidates[("s000", "fixed:4")].compare, 1750.0)


if __name__ == "__main__":
    unittest.main()
