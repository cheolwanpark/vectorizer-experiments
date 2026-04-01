import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3

from scripts.plot_results import (
    BenchMetricSummary,
    EmulateAggregate,
    VFCandidate,
    build_metric_summaries,
    load_emulate_data,
    parse_effective_cost,
    parse_vf_factor,
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

    def test_build_metric_summaries_ranks_by_effective_cost(self):
        candidates = {
            ("bench", "fixed:2"): VFCandidate(
                bench="bench",
                use_vf="fixed:2",
                raw_vf="2",
                raw_cost="24",
                cost=parse_effective_cost("24", "fixed:2"),
                selected=False,
            ),
            ("bench", "fixed:4"): VFCandidate(
                bench="bench",
                use_vf="fixed:4",
                raw_vf="4",
                raw_cost="32",
                cost=parse_effective_cost("32", "fixed:4"),
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
        self.assertEqual(point_by_vf["fixed:2"].cost, 12.0)
        self.assertEqual(point_by_vf["fixed:4"].cost, 8.0)
        self.assertEqual(summary.cost_best_vf, "fixed:4")

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


if __name__ == "__main__":
    unittest.main()
