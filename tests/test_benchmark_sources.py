import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import benchmark_sources


REPO_ROOT = Path(__file__).resolve().parents[1]
LOOPS_ROOT = REPO_ROOT / "emulator" / "benchmarks" / "TSVC_2" / "src" / "loops"


class BenchmarkSourcesTest(unittest.TestCase):
    def test_convert_loop_source_to_kernel_strips_runtime_wrapper(self):
        converted = benchmark_sources.convert_loop_source_to_kernel(
            "s111",
            (LOOPS_ROOT / "s111.c").read_text(encoding="utf-8"),
        )

        self.assertIn(f"/* {benchmark_sources.GENERATED_MINIMAL_MARKER}: s111 */", converted)
        self.assertIn('void kernel(void) {', converted)
        self.assertIn("for (int i = 1; i < LEN_1D; i += 2) {", converted)
        self.assertNotIn("initialise_arrays", converted)
        self.assertNotIn("gettimeofday", converted)
        self.assertNotIn("dummy(", converted)
        self.assertNotIn("for (int nl = 0;", converted)
        self.assertNotIn("func_args->", converted)

    def test_convert_loop_source_to_kernel_rewrites_structured_arg_info(self):
        converted = benchmark_sources.convert_loop_source_to_kernel(
            "s122",
            (LOOPS_ROOT / "s122.c").read_text(encoding="utf-8"),
        )

        self.assertIn("int n1 = tsvc_n1;", converted)
        self.assertIn("int n3 = tsvc_n3;", converted)
        self.assertIn("for (int i = n1-1; i < LEN_1D; i += n3) {", converted)
        self.assertNotIn("func_args->arg_info", converted)
        self.assertNotIn("x->a", converted)
        self.assertNotIn("x->b", converted)

    def test_convert_loop_source_to_kernel_uses_prepare_args_field_values(self):
        converted = benchmark_sources.convert_loop_source_to_kernel(
            "s4116",
            (LOOPS_ROOT / "s4116.c").read_text(encoding="utf-8"),
        )

        self.assertIn("int * __restrict__ ip = tsvc_ip;", converted)
        self.assertIn("int j = LEN_2D/2;", converted)
        self.assertIn("int inc = tsvc_n1;", converted)

    def test_convert_loop_source_to_kernel_keeps_helper_functions_and_compat_headers(self):
        converted = benchmark_sources.convert_loop_source_to_kernel(
            "s151",
            (LOOPS_ROOT / "s151.c").read_text(encoding="utf-8"),
        )

        self.assertIn("#include <math.h>", converted)
        self.assertIn("#include <stdlib.h>", converted)
        self.assertIn("#define ABS fabsf", converted)
        self.assertIn("extern real_t flat_2d_array[LEN_2D * LEN_2D];", converted)
        self.assertIn("extern real_t * __restrict__ xx;", converted)
        self.assertIn("void s151s(real_t a[LEN_1D], real_t b[LEN_1D],  int m)", converted)
        self.assertIn("s151s(a, b,  1);", converted)

    def test_convert_loop_source_to_kernel_rewrites_static_struct_initializer_args(self):
        converted = benchmark_sources.convert_loop_source_to_kernel(
            "s174",
            (LOOPS_ROOT / "s174.c").read_text(encoding="utf-8"),
        )

        self.assertIn("int M = LEN_1D/2;", converted)
        self.assertNotIn("int M = args;", converted)

    def test_resolve_benchmark_source_prefers_manual_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual = root / benchmark_sources.RUN_SRC_ROOT / "s999.c"
            manual.parent.mkdir(parents=True, exist_ok=True)
            manual.write_text('#include "common.h"\nvoid kernel(void) {}\n', encoding="utf-8")

            loop = root / benchmark_sources.TSVC_LOOP_ROOT / "s999.c"
            loop.parent.mkdir(parents=True, exist_ok=True)
            loop.write_text("unused", encoding="utf-8")

            resolved = benchmark_sources.resolve_benchmark_source(root, "s999")

        self.assertEqual(resolved.source_kind, "manual")
        self.assertEqual(resolved.source_path, manual)

    def test_resolve_benchmark_source_generates_missing_manual_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            loop = root / benchmark_sources.TSVC_LOOP_ROOT / "s111.c"
            loop.parent.mkdir(parents=True, exist_ok=True)
            loop.write_text((LOOPS_ROOT / "s111.c").read_text(encoding="utf-8"), encoding="utf-8")

            resolved = benchmark_sources.resolve_benchmark_source(root, "s111")
            generated_text = resolved.source_path.read_text(encoding="utf-8")

        self.assertEqual(resolved.source_kind, "generated")
        self.assertEqual(resolved.source_path, root / benchmark_sources.GENERATED_RUN_SRC_ROOT / "s111.c")
        self.assertIn("void kernel(void)", generated_text)

    def test_discover_catalog_workloads_reads_manifest_workloads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload_dir = root / "emulator" / "run" / "src" / "npb_is_s"
            workload_dir.mkdir(parents=True, exist_ok=True)
            (workload_dir / "is.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (workload_dir / "helper.c").write_text("void helper(void) {}\n", encoding="utf-8")
            (workload_dir / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "name": "npb_is_s",
                        "entry": {"mode": "main", "symbol": "main"},
                        "sources": ["is.c", "helper.c"],
                        "build": {"analysis_source": "is.c", "include_dirs": ["."]},
                    }
                ),
                encoding="utf-8",
            )

            workloads = benchmark_sources.discover_catalog_workloads(root)

        workload = next(workload for workload in workloads if workload.workload_id == "npb_is_s")
        self.assertEqual(workload.kind, "manifest")
        self.assertEqual(workload.analysis_source_path, (workload_dir / "is.c").resolve())
        self.assertEqual(workload.function_name, "main")

    def test_discover_catalog_workloads_rejects_duplicate_manifest_names(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a", "b"):
                workload_dir = root / "emulator" / "run" / "src" / name
                workload_dir.mkdir(parents=True, exist_ok=True)
                (workload_dir / f"{name}.c").write_text("void kernel(void) {}\n", encoding="utf-8")
                (workload_dir / "manifest.yaml").write_text(
                    json.dumps(
                        {
                            "name": "dup",
                            "sources": [f"{name}.c"],
                        }
                    ),
                    encoding="utf-8",
                )

            with self.assertRaises(RuntimeError):
                benchmark_sources.discover_catalog_workloads(root)

    def test_discover_catalog_workloads_filters_by_catalog_dir(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            tsvc_dir = root / "emulator" / "run" / "src" / "tsvc" / "s000"
            npb_dir = root / "emulator" / "run" / "src" / "npb" / "npb_is_s"
            tsvc_dir.mkdir(parents=True, exist_ok=True)
            npb_dir.mkdir(parents=True, exist_ok=True)
            (tsvc_dir / "s000.c").write_text("void kernel(void) {}\n", encoding="utf-8")
            (npb_dir / "is.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (tsvc_dir / "manifest.yaml").write_text(
                json.dumps({"name": "s000", "sources": ["s000.c"]}),
                encoding="utf-8",
            )
            (npb_dir / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "name": "npb_is_s",
                        "entry": {"mode": "main", "symbol": "main"},
                        "sources": ["is.c"],
                    }
                ),
                encoding="utf-8",
            )

            workloads = benchmark_sources.discover_catalog_workloads(root, "npb")

        self.assertEqual([workload.workload_id for workload in workloads], ["npb_is_s"])

    def test_analysis_source_resolution_marks_multiple_c_sources_unsupported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload_dir = root / "emulator" / "run" / "src" / "multi"
            workload_dir.mkdir(parents=True, exist_ok=True)
            (workload_dir / "a.c").write_text("void a(void) {}\n", encoding="utf-8")
            (workload_dir / "b.c").write_text("void b(void) {}\n", encoding="utf-8")
            (workload_dir / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "name": "multi",
                        "sources": ["a.c", "b.c"],
                    }
                ),
                encoding="utf-8",
            )

            workload = benchmark_sources.resolve_catalog_workload(root, "multi")

        self.assertIsNone(workload.analysis_source_path)
        self.assertEqual(workload.analysis_failure, "unsupported_analysis_source")

    def test_analysis_source_resolution_marks_assembly_only_manifest_unsupported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload_dir = root / "emulator" / "run" / "src" / "asm_only"
            workload_dir.mkdir(parents=True, exist_ok=True)
            (workload_dir / "kernel.S").write_text(".globl kernel\nkernel:\n\tret\n", encoding="utf-8")
            (workload_dir / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "name": "asm_only",
                        "sources": ["kernel.S"],
                    }
                ),
                encoding="utf-8",
            )

            workload = benchmark_sources.resolve_catalog_workload(root, "asm_only")

        self.assertIsNone(workload.analysis_source_path)
        self.assertEqual(workload.analysis_failure, "unsupported_analysis_source")

    def test_discover_catalog_workloads_accepts_cpp_manifest_sources(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload_dir = root / "emulator" / "run" / "src" / "parsec" / "streamcluster"
            workload_dir.mkdir(parents=True, exist_ok=True)
            (workload_dir / "streamcluster.cpp").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (workload_dir / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "name": "streamcluster",
                        "entry": {"mode": "main", "symbol": "main"},
                        "sources": ["streamcluster.cpp"],
                    }
                ),
                encoding="utf-8",
            )

            workload = benchmark_sources.resolve_catalog_workload(root, "streamcluster")

        self.assertEqual(workload.primary_source_path, (workload_dir / "streamcluster.cpp").resolve())
        self.assertIsNone(workload.analysis_source_path)
        self.assertEqual(workload.analysis_failure, "unsupported_analysis_source")


if __name__ == "__main__":
    unittest.main()
