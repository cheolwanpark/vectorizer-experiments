from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vf_performance.build import BuildManager
from vf_performance.cli import parse_args
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
    PipelineRunner,
    benchmark_requests,
    build_forced_vf_arg,
    discover_benchmarks,
    encode_use_vf,
    parse_vplan_output,
    resolve_llvm_tools,
    validate_runtime,
    RuntimeValidationError,
)
from vf_performance.qemu import ExecResult, QemuMetadata
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
    class _FakeBackend:
        def __init__(self):
            self.prepare_calls: list[bool] = []
            self.run_calls: list[tuple[list[str], object, object]] = []
            self.materialized_files: list[Path] = []
            self.materialized_dirs: list[Path] = []

        def prepare(self, *, sync_repo: bool = False) -> None:
            self.prepare_calls.append(sync_repo)

        def cleanup(self) -> None:
            return

        def command_path(self, path: Path) -> str:
            return f"/guest/{path.name}"

        def run(self, cmd: list[str], *, cwd=None, timeout=None) -> ExecResult:
            self.run_calls.append((cmd, cwd, timeout))
            if cmd and cmd[0] == "test":
                return ExecResult(0, "", "")
            return ExecResult(
                0,
                "Loop \tTime(sec) \tChecksum\n      77\t1.000000\nExiting @ tick 123\n",
                "",
            )

        def materialize_file(self, path: Path) -> None:
            self.materialized_files.append(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")

        def materialize_dir(self, path: Path) -> None:
            self.materialized_dirs.append(path)
            path.mkdir(parents=True, exist_ok=True)
            (path / "stats.txt").write_text("system.cpu.numCycles                         99\n")

    def _touch_executable(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)

    def _make_runtime(
        self,
        rvv_root: Path,
        *,
        tools: dict[str, str],
        bench_filters: list[str] | None = None,
    ) -> AppRuntimeConfig:
        return AppRuntimeConfig(
            rvv_root=str(rvv_root),
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=bench_filters or [],
            no_cache=False,
            cache_dir=str(rvv_root / ".cache"),
            tools=tools,
        )

    def _make_qemu_metadata(self, state_dir: Path) -> QemuMetadata:
        return QemuMetadata(
            ssh_user="vf",
            ssh_port=10022,
            ssh_key_path=str(state_dir / "id_ed25519"),
            guest_workspace="/home/vf/work/vf-performance",
            guest_cache_dir="/home/vf/work/vf-performance/.cache/vf-performance",
            disk_path=str(state_dir / "guest.qcow2"),
            seed_iso_path=str(state_dir / "seed.iso"),
            pidfile=str(state_dir / "qemu.pid"),
            serial_log=str(state_dir / "serial.log"),
            tools={
                "clang": "/guest/clang",
                "opt": "/guest/opt",
                "sysroot": "/guest/sysroot",
                "gem5": "/guest/gem5.opt",
            },
            tool_versions={
                "clang": "clang version 1",
                "opt": "opt version 1",
            },
        )

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
        benchmarks = discover_benchmarks(rvv_root, filters=["s123"])
        self.assertEqual(len(benchmarks), 1)
        self.assertEqual(benchmarks[0].benchmark, "s123")

    def test_parse_tsvc_kernel_cycles(self) -> None:
        text = "Loop \tTime(sec) \tChecksum\n      1234\t5.000000\n"
        self.assertEqual(parse_tsvc_kernel_cycles(text), 1234)

    def test_parse_args_defaults_to_qemu_on_darwin(self) -> None:
        with patch("vf_performance.cli.default_executor", return_value="qemu"):
            with patch("sys.argv", ["vf-performance"]):
                args = parse_args()
        self.assertEqual(args.executor, "qemu")

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

    def test_validate_runtime_reports_missing_sysroot_headers_and_gem5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rvv"
            loop_dir = root / "benchmarks" / "TSVC_2" / "src" / "loops"
            loop_dir.mkdir(parents=True)
            (loop_dir / "s000.c").write_text("int main(void) { return 0; }\n")

            clang = root / "bin" / "clang"
            opt = root / "bin" / "opt"
            self._touch_executable(clang)
            self._touch_executable(opt)
            (root / "sysroot").mkdir(parents=True)

            runtime = self._make_runtime(
                root,
                tools={
                    "clang": str(clang),
                    "opt": str(opt),
                    "sysroot": str(root / "sysroot"),
                    "gem5": str(root / "gem5" / "build" / "RISCV" / "gem5.opt"),
                },
            )

            with self.assertRaises(RuntimeValidationError) as ctx:
                validate_runtime(runtime)

            message = str(ctx.exception)
            self.assertIn("math.h not found", message)
            self.assertIn("gem5 binary not found", message)

    def test_validate_runtime_rejects_unknown_benchmarks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rvv"
            loop_dir = root / "benchmarks" / "TSVC_2" / "src" / "loops"
            loop_dir.mkdir(parents=True)
            (loop_dir / "s000.c").write_text("int main(void) { return 0; }\n")

            sysroot = root / "sysroot" / "usr" / "include"
            sysroot.mkdir(parents=True)
            (sysroot / "math.h").write_text("/* math */\n")

            clang = root / "bin" / "clang"
            opt = root / "bin" / "opt"
            gem5 = root / "gem5" / "build" / "RISCV" / "gem5.opt"
            se_py = root / "gem5" / "configs" / "example" / "se.py"
            self._touch_executable(clang)
            self._touch_executable(opt)
            self._touch_executable(gem5)
            se_py.parent.mkdir(parents=True, exist_ok=True)
            se_py.write_text("# gem5\n")

            runtime = self._make_runtime(
                root,
                tools={
                    "clang": str(clang),
                    "opt": str(opt),
                    "sysroot": str(root / "sysroot"),
                    "gem5": str(gem5),
                },
                bench_filters=["missing"],
            )

            with self.assertRaises(RuntimeValidationError) as ctx:
                validate_runtime(runtime)
            self.assertIn("unknown benchmarks requested: missing", str(ctx.exception))

    def test_validate_runtime_qemu_reports_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rvv_root = Path.cwd() / "rvv-poc-main"
            self.assertTrue(rvv_root.exists())
            root = Path(tmp) / "vf-performance"

            runtime = AppRuntimeConfig(
                rvv_root=str(rvv_root),
                llvm_custom=None,
                len_1d=32000,
                jobs=1,
                sim_jobs=1,
                bench_filters=[],
                no_cache=False,
                cache_dir=str(root / ".cache" / "vf-performance"),
                tools={"clang": "", "opt": "", "sysroot": "", "gem5": ""},
                executor="qemu",
                qemu_state_dir=str(root / ".cache" / "vf-performance" / "qemu"),
            )

            with self.assertRaises(RuntimeValidationError) as ctx:
                validate_runtime(runtime)
            self.assertIn("QEMU metadata not found", str(ctx.exception))

    def test_validate_runtime_qemu_uses_guest_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rvv_root = Path.cwd() / "rvv-poc-main"
            self.assertTrue(rvv_root.exists())
            root = Path(tmp) / "vf-performance"
            state_dir = root / ".cache" / "vf-performance" / "qemu"
            state_dir.mkdir(parents=True)
            fake_backend = self._FakeBackend()
            metadata = self._make_qemu_metadata(state_dir)

            runtime = AppRuntimeConfig(
                rvv_root=str(rvv_root),
                llvm_custom=None,
                len_1d=32000,
                jobs=1,
                sim_jobs=1,
                bench_filters=[],
                no_cache=False,
                cache_dir=str(root / ".cache" / "vf-performance"),
                tools=dict(metadata.tools),
                executor="qemu",
                qemu_state_dir=str(state_dir),
            )

            with patch("vf_performance.pipeline.load_qemu_metadata", return_value=metadata):
                with patch("vf_performance.pipeline.create_execution_backend", return_value=fake_backend):
                    validate_runtime(runtime)

            self.assertEqual(fake_backend.prepare_calls, [False])

    def test_resolve_llvm_tools_prefers_env_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rvv"
            llvm_build = root / "custom-llvm"
            riscv_tools = root / "custom-riscv-tools"
            gem5_dir = root / "custom-gem5"

            self._touch_executable(llvm_build / "bin" / "clang")
            self._touch_executable(llvm_build / "bin" / "opt")
            (riscv_tools / "riscv64-unknown-linux-gnu" / "sysroot" / "usr" / "include").mkdir(parents=True)
            self._touch_executable(gem5_dir / "build" / "RISCV" / "gem5.opt")

            with patch.dict(
                os.environ,
                {
                    "LLVM_BUILD_DIR": str(llvm_build),
                    "RISCV_TOOLS_PREFIX": str(riscv_tools),
                    "GEM5_DIR": str(gem5_dir),
                },
                clear=False,
            ):
                tools = resolve_llvm_tools(None, root)

            self.assertEqual(Path(tools["clang"]).resolve(), (llvm_build / "bin" / "clang").resolve())
            self.assertEqual(Path(tools["opt"]).resolve(), (llvm_build / "bin" / "opt").resolve())
            self.assertEqual(
                Path(tools["sysroot"]).resolve(),
                (riscv_tools / "riscv64-unknown-linux-gnu" / "sysroot").resolve(),
            )
            self.assertEqual(
                Path(tools["gem5"]).resolve(),
                (gem5_dir / "build" / "RISCV" / "gem5.opt").resolve(),
            )

    def test_resolve_llvm_tools_falls_back_per_tool_for_partial_custom_llvm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rvv"
            llvm_build = root / "custom-llvm"
            self._touch_executable(llvm_build / "bin" / "opt")

            def fake_which(name: str) -> str | None:
                mapping = {
                    "clang": "/opt/mock/bin/clang",
                    "opt": "/opt/mock/bin/opt",
                }
                return mapping.get(name)

            with patch.dict(os.environ, {"LLVM_CUSTOM": str(llvm_build / "bin")}, clear=False):
                with patch("vf_performance.pipeline.shutil.which", side_effect=fake_which):
                    tools = resolve_llvm_tools(None, root)

            self.assertEqual(tools["clang"], "/opt/mock/bin/clang")
            self.assertEqual(Path(tools["opt"]).resolve(), (llvm_build / "bin" / "opt").resolve())

    def test_cache_keys_change_when_sysroot_or_gem5_changes(self) -> None:
        runtime_a = AppRuntimeConfig(
            rvv_root="/tmp/rvv",
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=[],
            no_cache=False,
            cache_dir="/tmp/cache",
            tools={
                "clang": "/tmp/clang",
                "opt": "/tmp/opt",
                "sysroot": "/tmp/sysroot-a",
                "gem5": "/tmp/gem5-a",
            },
        )
        runtime_b = AppRuntimeConfig(
            rvv_root="/tmp/rvv",
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=[],
            no_cache=False,
            cache_dir="/tmp/cache",
            tools={
                "clang": "/tmp/clang",
                "opt": "/tmp/opt",
                "sysroot": "/tmp/sysroot-b",
                "gem5": "/tmp/gem5-b",
            },
        )

        with patch("vf_performance.storage.tool_version", return_value="llvm-test"):
            from vf_performance.storage import analysis_cache_key, run_cache_key

            self.assertNotEqual(
                analysis_cache_key(runtime_a, "s000", "/tmp/s000.c"),
                analysis_cache_key(runtime_b, "s000", "/tmp/s000.c"),
            )
            self.assertNotEqual(
                run_cache_key(runtime_a, "s000", "/tmp/s000.c", 0, "4", "forced"),
                run_cache_key(runtime_b, "s000", "/tmp/s000.c", 0, "4", "forced"),
            )

    def test_cache_keys_change_when_executor_changes(self) -> None:
        runtime_local = AppRuntimeConfig(
            rvv_root="/tmp/rvv",
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=[],
            no_cache=False,
            cache_dir="/tmp/cache",
            tools={"clang": "/tmp/clang", "opt": "/tmp/opt", "sysroot": "/tmp/sysroot", "gem5": "/tmp/gem5"},
            executor="local",
        )
        runtime_qemu = AppRuntimeConfig(
            rvv_root="/tmp/rvv",
            llvm_custom=None,
            len_1d=32000,
            jobs=1,
            sim_jobs=1,
            bench_filters=[],
            no_cache=False,
            cache_dir="/tmp/cache",
            tools={"clang": "/guest/clang", "opt": "/guest/opt", "sysroot": "/guest/sysroot", "gem5": "/guest/gem5"},
            executor="qemu",
            guest_workspace="/home/vf/work/vf-performance",
            tool_versions={"clang": "clang version 1", "opt": "opt version 1"},
        )

        with patch("vf_performance.storage.tool_version", return_value="local-version"):
            from vf_performance.storage import analysis_cache_key, run_cache_key

            self.assertNotEqual(
                analysis_cache_key(runtime_local, "s000", "/tmp/s000.c"),
                analysis_cache_key(runtime_qemu, "s000", "/tmp/s000.c"),
            )
            self.assertNotEqual(
                run_cache_key(runtime_local, "s000", "/tmp/s000.c", 0, "4", "forced"),
                run_cache_key(runtime_qemu, "s000", "/tmp/s000.c", 0, "4", "forced"),
            )

    def test_build_binary_includes_forced_vf_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rvv"
            src_dir = root / "benchmarks" / "TSVC_2" / "src"
            loops_dir = src_dir / "loops"
            loops_dir.mkdir(parents=True)
            for name in ("dummy.c", "common.c", "data.c", "single_runner.c"):
                (src_dir / name).write_text("int x;\n")
            loop_source = loops_dir / "s000.c"
            loop_source.write_text("int x;\n")

            runtime = self._make_runtime(
                root,
                tools={
                    "clang": "/tmp/clang",
                    "opt": "/tmp/opt",
                    "sysroot": str(root / "sysroot"),
                    "gem5": str(root / "gem5" / "build" / "RISCV" / "gem5.opt"),
                },
            )
            manager = BuildManager(runtime, Path(tmp) / "cache")
            commands: list[list[str]] = []

            def fake_run_checked(cmd: list[str], cwd: Path) -> None:
                commands.append(cmd)
                output = Path(cmd[cmd.index("-o") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("")

            with patch.object(manager, "_run_checked", side_effect=fake_run_checked):
                elf_path, _ = manager.build_binary(
                    "s000",
                    loop_source,
                    "forced-key",
                    forced_vf_arg="fixed:4",
                )

            compile_cmd = next(
                cmd for cmd in commands if str(loop_source) in cmd and "-c" in cmd
            )
            self.assertIn("-mllvm", compile_cmd)
            self.assertIn("-vplan-use-vf=fixed:4", compile_cmd)
            self.assertTrue(elf_path.exists())

    def test_pipeline_runner_routes_gem5_through_backend_in_qemu_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vf-performance"
            loop_dir = root / "rvv-poc-main" / "benchmarks" / "TSVC_2" / "src" / "loops"
            loop_dir.mkdir(parents=True)
            source_path = loop_dir / "s000.c"
            source_path.write_text("int main(void) { return 0; }\n")

            runtime = AppRuntimeConfig(
                rvv_root=str(root / "rvv-poc-main"),
                llvm_custom=None,
                len_1d=32000,
                jobs=1,
                sim_jobs=1,
                bench_filters=[],
                no_cache=False,
                cache_dir=str(root / ".cache" / "vf-performance"),
                tools={
                    "clang": "/guest/clang",
                    "opt": "/guest/opt",
                    "sysroot": "/guest/sysroot",
                    "gem5": "/guest/gem5/build/RISCV/gem5.opt",
                },
                executor="qemu",
                guest_workspace="/home/vf/work/vf-performance",
                tool_versions={"clang": "clang version 1", "opt": "opt version 1"},
            )
            backend = self._FakeBackend()
            runner = PipelineRunner(runtime, backend=backend)

            request = type(
                "Req",
                (),
                {
                    "benchmark": "s000",
                    "category": "Linear",
                    "source_path": str(source_path),
                    "loop_index": None,
                    "requested_vf": None,
                    "mode": "default",
                },
            )()
            elf_path = Path(runtime.cache_dir) / "artifacts" / "s000.elf"
            with patch.object(runner.build_manager, "build_binary", return_value=(elf_path, "clang ...")):
                result = runner._compile_and_run(
                    request,
                    selected_vf=None,
                    selected_plan=None,
                    selected_cost=None,
                )

            self.assertEqual(result.status, "OK")
            self.assertEqual(result.kernel_cycles, 77)
            self.assertEqual(result.total_cycles, 99)
            self.assertTrue(any("--outdir=/guest/" in item for call, _, _ in backend.run_calls for item in call))
            self.assertTrue(backend.materialized_dirs)


if __name__ == "__main__":
    unittest.main()
