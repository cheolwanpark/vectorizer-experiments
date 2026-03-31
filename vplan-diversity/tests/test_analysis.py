from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vplan_diversity.models import AppRuntimeConfig, BenchResult, LoopInfo, VFCost, VPlan
from vplan_diversity.pipeline import (
    analyze_function_vplans,
    build_forced_vf_arg,
    encode_use_vf,
    extract_benchmark_source,
    extract_selected_vplan_dumps,
    pick_highest_vf,
)


SUCCESS_LOG = """\
LV: Loop[0] forcing VF 4
LV: Loop[0] path=inner plans=1
LV:   VPlan[0] VFs={2,4}
LV:   selected VF=4 plan=0
LV: Loop[0] selected VF=4 plan=0
LV: Loop[0] selected VPlan dump follows
VPlan 'Initial VPlan for VF={4},UF>=1' {
  vector.body:
    WIDEN ir<%0> = load vp<%ptr>
}
LV: Loop[0] bypassing interleave selection for forced VF
"""


MISSING_DUMP_LOG = """\
LV: Loop[0] forcing VF 4
LV: Loop[0] path=inner plans=1
LV:   VPlan[0] VFs={4}
LV:   selected VF=4 plan=0
"""


MISMATCH_LOG = """\
LV: Loop[0] forcing VF 4
LV: Loop[0] path=inner plans=2
LV:   VPlan[0] VFs={2,4}
LV:   VPlan[1] VFs={8}
LV:   selected VF=8 plan=1
LV: Loop[0] selected VF=8 plan=1
LV: Loop[0] selected VPlan dump follows
VPlan 'Initial VPlan for VF={8},UF>=1' {
  vector.body:
    WIDEN ir<%0> = load vp<%ptr>
}
LV: Loop[0] bypassing interleave selection for forced VF
"""


TSVC_INC_TEXT = """\
#if TESTS & CONTROL_FLOW

int s000()
{
    int total = 0;
    for (int i = 0; i < 8; i++) {
        total += i;
    }
    return total;
}

int s111()
{
    return 1;
}

#endif
"""


def make_result() -> BenchResult:
    return BenchResult(
        func_name="s000",
        category="CONTROL_FLOW",
        loops=[
            LoopInfo(
                index=0,
                path="inner",
                plan_count=1,
                plans=[
                    VPlan(
                        index=0,
                        vfs=["2", "4"],
                        costs=[VFCost(vf="2", cost=30), VFCost(vf="4", cost=20)],
                    )
                ],
                selected_vf="4",
                selected_plan=0,
            )
        ],
        error=None,
        raw_output="",
    )


def make_runtime(tsvc_dir: str) -> AppRuntimeConfig:
    return AppRuntimeConfig(
        variant="dbl",
        vlen=256,
        llvm_custom="/tmp/llvm-custom",
        tsvc_dir=tsvc_dir,
        tools={"clang": "clang", "opt": "opt", "llvm-extract": "llvm-extract"},
    )


class AnalysisHelpersTest(unittest.TestCase):
    def test_extract_benchmark_source_returns_one_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tsc_inc = Path(tmpdir) / "tsc.inc"
            tsc_inc.write_text(TSVC_INC_TEXT)

            source, source_path = extract_benchmark_source("s000", Path(tmpdir))

        self.assertEqual(source_path, str(tsc_inc))
        self.assertIn("int s000()", source)
        self.assertIn("total += i;", source)
        self.assertNotIn("int s111()", source)

    def test_pick_highest_vf_uses_numeric_magnitude(self):
        self.assertEqual(pick_highest_vf(["1", "8", "4"]), "8")

    def test_build_forced_vf_arg_uses_positional_placeholders(self):
        result = BenchResult(
            func_name="s001",
            category="CONTROL_FLOW",
            loops=[
                LoopInfo(0, "inner", 1, [VPlan(0, ["2"], [])], "2", 0),
                LoopInfo(1, "inner", 1, [VPlan(0, ["4"], [])], "4", 0),
                LoopInfo(2, "inner", 1, [VPlan(0, ["8"], [])], "8", 0),
            ],
            error=None,
            raw_output="",
        )
        self.assertEqual(build_forced_vf_arg(result, 1, "4"), "-,fixed:4,-")

    def test_encode_use_vf_supports_fixed_and_scalable_forms(self):
        self.assertEqual(encode_use_vf("16"), "fixed:16")
        self.assertEqual(encode_use_vf("vscale x 4"), "scalable:4")

    def test_extract_selected_vplan_dumps_returns_full_block(self):
        dumps = extract_selected_vplan_dumps(SUCCESS_LOG)
        self.assertIn(0, dumps)
        self.assertIn("VPlan 'Initial VPlan", dumps[0])
        self.assertIn("WIDEN ir<%0>", dumps[0])


class AnalyzeFunctionVPlansTest(unittest.TestCase):
    def _write_log(self, root: str, text: str) -> Path:
        log_path = Path(root) / ".build" / "dbl" / "s000" / "opt.verbose.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(text)
        return log_path

    def _write_tsc_inc(self, root: str, text: str = TSVC_INC_TEXT) -> Path:
        tsc_inc = Path(root) / "tsc.inc"
        tsc_inc.write_text(text)
        return tsc_inc

    def test_analyze_function_vplans_success_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_log(tmpdir, SUCCESS_LOG)
            self._write_tsc_inc(tmpdir)
            runtime = make_runtime(tmpdir)
            result = make_result()

            with patch("vplan_diversity.pipeline.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["make"], returncode=0, stdout="", stderr=""
                )
                report = analyze_function_vplans(result, runtime)

            self.assertEqual(len(report.entries), 1)
            entry = report.entries[0]
            self.assertEqual(entry.status, "ok")
            self.assertEqual(entry.forced_vf, "4")
            self.assertIn("USE_VF=fixed:4", entry.command)
            self.assertIn("OPT=opt", entry.command)
            self.assertIn("# VPlan Analysis: `s000`", report.markdown_report)
            self.assertIn("## Benchmark C Source", report.markdown_report)
            self.assertIn("```c", report.markdown_report)
            self.assertIn("int s000()", report.markdown_report)
            self.assertIn("| 0 | 0 | `4` |", report.markdown_report)
            self.assertIn("```text", report.markdown_report)

    def test_analyze_function_vplans_marks_missing_dump_as_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_log(tmpdir, MISSING_DUMP_LOG)
            self._write_tsc_inc(tmpdir)
            runtime = make_runtime(tmpdir)
            result = make_result()

            with patch("vplan_diversity.pipeline.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["make"], returncode=0, stdout="", stderr=""
                )
                report = analyze_function_vplans(result, runtime)

            entry = report.entries[0]
            self.assertEqual(entry.status, "error")
            self.assertIn("selected dump missing", entry.message)

    def test_analyze_function_vplans_marks_selection_mismatch_as_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_log(tmpdir, MISMATCH_LOG)
            self._write_tsc_inc(tmpdir)
            runtime = make_runtime(tmpdir)
            result = make_result()

            with patch("vplan_diversity.pipeline.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["make"], returncode=0, stdout="", stderr=""
                )
                report = analyze_function_vplans(result, runtime)

            entry = report.entries[0]
            self.assertEqual(entry.status, "warning")
            self.assertIn("expected VF=4 plan=0", entry.message)
            self.assertIn("got VF=8 plan=1", entry.message)

    def test_analyze_function_vplans_keeps_report_when_source_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_log(tmpdir, SUCCESS_LOG)
            runtime = make_runtime(tmpdir)
            result = make_result()

            with patch("vplan_diversity.pipeline.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["make"], returncode=0, stdout="", stderr=""
                )
                report = analyze_function_vplans(result, runtime)

            self.assertEqual(report.source_code, "")
            self.assertIn("## Benchmark C Source", report.markdown_report)
            self.assertIn("_Benchmark source unavailable._", report.markdown_report)
            self.assertIn("| 0 | 0 | `4` |", report.markdown_report)


if __name__ == "__main__":
    unittest.main()
