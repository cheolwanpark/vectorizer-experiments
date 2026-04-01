import unittest

from scripts.plot_results import (
    BenchMetricSummary,
    EmulateAggregate,
    VFCandidate,
    build_metric_summaries,
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


if __name__ == "__main__":
    unittest.main()
