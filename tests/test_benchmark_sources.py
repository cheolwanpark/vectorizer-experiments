import unittest
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


if __name__ == "__main__":
    unittest.main()
