import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_KERNEL = REPO_ROOT / "emulator" / "run" / "build-kernel"


class BuildKernelTest(unittest.TestCase):
    def test_tsvc_mode_does_not_reintroduce_arrays_runtime_sources(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        support_sources_offset = script.index("SUPPORT_SRCS=()")
        block_start = script.index('if [[ "$TSVC_MODE" -eq 1 ]]; then', support_sources_offset)
        block_end = script.index('OBJECT_COMPILE_FLAGS=("${COMPILE_FLAGS[@]}" -O3)', block_start)
        tsvc_override_block = script[block_start:block_end]
        self.assertNotIn('"${SCRIPT_DIR}/common/arrays.c"', tsvc_override_block)


if __name__ == "__main__":
    unittest.main()
