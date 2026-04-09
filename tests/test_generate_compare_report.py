import unittest
from pathlib import Path

from scripts.generate_compare_report import (
    ROOT,
    classify_benches,
    load_bench_summaries,
    render_report,
    resolve_input,
    select_case_benches,
)


class GenerateCompareReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.emulate_db = resolve_input(ROOT, "", "emulate-result-*.sqlite")
        cls.profile_db = resolve_input(ROOT, "", "profile-result-*.sqlite")
        cls.rvv = load_bench_summaries(cls.emulate_db)
        cls.intel = load_bench_summaries(cls.profile_db)

    def test_classification_uses_current_thresholds(self):
        categories = classify_benches(self.intel, self.rvv)
        self.assertIn("s111", categories["both"])
        self.assertIn("s2275", categories["intel_only"])
        self.assertIn("s351", categories["rvv_only"])

    def test_selection_prefers_current_representative_cases(self):
        selected = select_case_benches(self.intel, self.rvv)
        self.assertEqual(
            selected,
            [
                ("both", "s111"),
                ("both", "s2710"),
                ("intel_only", "s2275"),
                ("intel_only", "s257"),
                ("rvv_only", "s351"),
                ("rvv_only", "s452"),
            ],
        )

    def test_rendered_report_uses_current_db_and_values(self):
        report = render_report(self.emulate_db, self.profile_db, self.intel, self.rvv)
        self.assertIn("artifacts/profile-result-202604090713.sqlite", report)
        self.assertNotIn("profile-result-202604070505.sqlite", report)
        self.assertIn("| Intel | `default` / 7884 | `fixed:2` / 2030 | 0.7425 |", report)
        self.assertIn("| RVV | `default` / 115427 | `fixed:1` / 7168 | 0.9379 |", report)
        for bench in ["s111", "s2710", "s2275", "s257", "s351", "s452"]:
            self.assertIn(f"`{bench}`", report)


if __name__ == "__main__":
    unittest.main()
