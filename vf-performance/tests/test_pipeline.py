from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vf_performance.gem5 import parse_gem5_total_cycles, parse_tsvc_kernel_cycles
from vf_performance.models import (
    AppRuntimeConfig,
    BenchmarkAnalysis,
    LoopAnalysis,
    RunResult,
    VFCost,
    VPlan,
)
from vf_performance.pipeline import (
    benchmark_requests,
    build_forced_vf_arg,
    discover_benchmarks,
    encode_use_vf,
    parse_vplan_output,
)
from vf_performance.storage import export_runs_csv, export_session_json


SAMPLE_VPLAN = """
LV: Loop[0] path=vector plans=2
LV:   VPlan[0] VFs={2, 4}
LV:   VF=2 cost=32
LV:   VF=4 cost=18
LV:   VPlan[1] VFs={vscale x 2}
LV:   VF=vscale x 2 cost=22
LV:   selected VF=4 plan=0
LV: Loop[1] path=epilogue plans=1
LV:   VPlan[0] VFs={2}
LV:   VF=2 cost=9
LV:   selected VF=2 plan=0
""".strip()


class PipelineTests(unittest.TestCase):
    def test_parse_vplan_output_handles_multiple_loops(self) -> None:
        loops = parse_vplan_output(SAMPLE_VPLAN)
        self.assertEqual(len(loops), 2)
        self.assertEqual(loops[0].plans[0].costs[1].cost, 18)
        self.assertEqual(loops[0].selected_vf, "4")
        self.assertEqual(loops[1].selected_plan, 0)

    def test_encode_use_vf_supports_fixed_and_scalable(self) -> None:
        self.assertEqual(encode_use_vf("4"), "fixed:4")
        self.assertEqual(encode_use_vf("vscale x 2"), "scalable:2")

    def test_build_forced_vf_arg_uses_placeholders(self) -> None:
        analysis = BenchmarkAnalysis(
            benchmark="s000",
            source_path="/tmp/s000.c",
            category="Linear",
            raw_output="",
            loops=[
                LoopAnalysis(index=0, path="vector", plan_count=1, plans=[]),
                LoopAnalysis(index=1, path="vector", plan_count=1, plans=[]),
                LoopAnalysis(index=2, path="vector", plan_count=1, plans=[]),
            ],
        )
        self.assertEqual(build_forced_vf_arg(analysis, 1, "4"), "-,fixed:4,-")

    def test_benchmark_requests_expand_default_and_forced_rows(self) -> None:
        analysis = BenchmarkAnalysis(
            benchmark="s000",
            source_path="/tmp/s000.c",
            category="Linear",
            raw_output="",
            loops=[
                LoopAnalysis(
                    index=0,
                    path="vector",
                    plan_count=2,
                    plans=[
                        VPlan(index=0, vfs=["2", "4"], costs=[VFCost("2", 12), VFCost("4", 8)]),
                        VPlan(index=1, vfs=["4", "vscale x 2"], costs=[VFCost("4", 8), VFCost("vscale x 2", 10)]),
                    ],
                )
            ],
        )
        requests = benchmark_requests(analysis)
        self.assertEqual(requests[0].mode, "default")
        self.assertEqual([item.requested_vf for item in requests[1:]], ["2", "4", "vscale x 2"])

    def test_discover_benchmarks_applies_filters(self) -> None:
        rvv_root = Path.cwd() / "rvv-poc-main"
        benchmarks = discover_benchmarks(rvv_root, filters=["s351"])
        self.assertEqual(len(benchmarks), 1)
        self.assertEqual(benchmarks[0].benchmark, "s351")

    def test_parse_tsvc_kernel_cycles(self) -> None:
        text = "Loop \tTime(sec) \tChecksum\n      1234\t5.000000\n"
        self.assertEqual(parse_tsvc_kernel_cycles(text), 1234)

    def test_parse_gem5_total_cycles_prefers_stats(self) -> None:
        stats = "system.cpu.numCycles                         4567\n"
        self.assertEqual(parse_gem5_total_cycles("Exiting @ tick 123", stats), 4567)

    def test_export_helpers_write_files(self) -> None:
        runtime = AppRuntimeConfig(
            rvv_root="/tmp/rvv",
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=[],
            no_cache=False,
            cache_dir="/tmp/cache",
            tools={"clang": "clang", "opt": "opt", "gem5": "gem5"},
        )
        run = RunResult(
            benchmark="s000",
            category="Linear",
            source_path="/tmp/s000.c",
            loop_index=0,
            requested_vf="4",
            mode="forced",
            selected_vf="4",
            selected_plan=0,
            selected_cost=10,
            kernel_cycles=100,
            total_cycles=200,
            wall_time_s=1.0,
            status="OK",
            command="clang ...",
            artifact_path="/tmp/s000.elf",
            log_path="/tmp/s000.log",
            out_dir="/tmp/m5out",
        )
        analysis = BenchmarkAnalysis(
            benchmark="s000",
            source_path="/tmp/s000.c",
            category="Linear",
            loops=[],
            raw_output="",
        )

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "runs.csv"
            json_path = Path(tmp) / "session.json"
            export_runs_csv(csv_path, [run])
            export_session_json(json_path, runtime, type("Session", (), {"analyses": [analysis], "runs": [run]})())
            self.assertTrue(csv_path.exists())
            data = json.loads(json_path.read_text())
            self.assertEqual(data["runs"][0]["benchmark"], "s000")


if __name__ == "__main__":
    unittest.main()
