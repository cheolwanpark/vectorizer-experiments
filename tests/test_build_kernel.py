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

    def test_forced_vf_build_persists_assembly_artifact(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        forced_vf_block_start = script.index('verify_forced_vector_ir "$OPT_LL" "$USE_VF" "$OPT_LOG"')
        forced_vf_block_end = script.index("OBJECTS=()", forced_vf_block_start)
        forced_vf_block = script[forced_vf_block_start:forced_vf_block_end]
        self.assertIn('ASM_OUT="${BASE_PATH}.s"', forced_vf_block)
        self.assertIn('echo "Artifacts: $RAW_LL $PREVEC_LL $OPT_LL $OPT_LOG $ASM_OUT"', script)


if __name__ == "__main__":
    unittest.main()
