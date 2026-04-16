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

    def test_forced_vf_validation_only_hard_fails_on_opt_rejection(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        verify_block_start = script.index("verify_forced_vector_ir() {")
        verify_block_end = script.index("validate_vplan_use_vf()", verify_block_start)
        verify_block = script[verify_block_start:verify_block_end]

        self.assertIn('die "Forced VF optimization was rejected by opt. Log: ${log_path}"', verify_block)
        self.assertNotIn('die "Forced VF verification failed for ${first_entry}. Saved IR: ${ir_path}"', verify_block)
        self.assertIn('warn "Forced VF ${first_entry} did not leave a final vector.body marker in ${ir_path}; continuing because late vector passes may rewrite the loop shape"', verify_block)
        self.assertIn('warn "Forced VF ${first_entry} did not leave an exact final VF type marker in ${ir_path}; continuing because late vector passes may rewrite the final IR"', verify_block)

    def test_forced_vf_build_persists_assembly_artifact(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        forced_vf_block_start = script.index('verify_forced_vector_ir "$OPT_LL" "$USE_VF" "$OPT_LOG"')
        forced_vf_block_end = script.index("OBJECTS=()", forced_vf_block_start)
        forced_vf_block = script[forced_vf_block_start:forced_vf_block_end]
        self.assertIn('ASM_OUT="${BASE_PATH}.s"', script)
        self.assertIn('echo "Artifacts: $OPT_LL $ASM_OUT"', script)
        self.assertNotIn('RAW_LL="${BASE_PATH}.raw.ll"', script)
        self.assertNotIn('PREVEC_LL="${BASE_PATH}.prevec.ll"', script)

    def test_default_build_uses_shared_llvm_pipeline(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        self.assertIn('PIPELINE_HELPER="$(resolve_pipeline_helper)" || die "llvm_pipeline.py not found"', script)
        self.assertIn('python3', script)
        self.assertIn('build-artifacts', script)
        self.assertNotIn('emit_default_build_artifacts "$IR_SOURCE" "$OUTPUT"', script)

    def test_extra_opt_flags_are_forwarded_to_pipeline(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        self.assertIn('echo "  --optflags=FLAGS Additional opt flags"', script)
        self.assertIn('--optflags=*) EXTRA_OPT_FLAGS="${1#*=}" ;;', script)
        self.assertIn('append_split_flags "$EXTRA_OPT_FLAGS" OPT_FLAGS', script)
        self.assertIn('PIPELINE_CMD+=("--opt-flag=$flag")', script)

    def test_generated_mode_adds_tsvc_runtime_without_full_tsvc_runtime_sources(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        block_start = script.index('elif [[ "$GENERATED_MODE" -eq 1 ]]; then', script.index("SUPPORT_SRCS=()"))
        block_end = script.index('\nfi\n\nOBJECT_COMPILE_FLAGS=("${COMPILE_FLAGS[@]}" -O3)', block_start)
        generated_block = script[block_start:block_end]

        self.assertIn('"${SCRIPT_DIR}/common/tsvc_runtime.c"', generated_block)
        self.assertNotIn('"${SCRIPT_DIR}/../benchmarks/TSVC_2/src/common.c"', generated_block)
        self.assertNotIn('"${SCRIPT_DIR}/../benchmarks/TSVC_2/src/data.c"', generated_block)
        self.assertNotIn('"${SCRIPT_DIR}/../benchmarks/TSVC_2/src/dummy.c"', generated_block)

    def test_generated_mode_inherits_tsvc_header_include_path(self):
        script = BUILD_KERNEL.read_text(encoding="utf-8")
        block_start = script.index('elif [[ "$GENERATED_MODE" -eq 1 ]]; then')
        block_end = script.index("LINK_FLAGS=(", block_start)
        generated_flags_block = script[block_start:block_end]

        self.assertIn('-I"${SCRIPT_DIR}/../benchmarks/TSVC_2/src"', generated_flags_block)
        self.assertNotIn("-DTSVC_MEASURE_CYCLES", generated_flags_block)

    def test_generated_runtime_exports_tsvc_compat_arrays(self):
        arrays_header = (REPO_ROOT / "emulator" / "run" / "common" / "arrays.h").read_text(encoding="utf-8")
        arrays_source = (REPO_ROOT / "emulator" / "run" / "common" / "arrays.c").read_text(encoding="utf-8")

        self.assertIn("flat_2d_array", arrays_header)
        self.assertIn("x[LEN_1D]", arrays_header)
        self.assertIn("real_t * __restrict__ xx;", arrays_header)
        self.assertIn("flat_2d_array[LEN_2D * LEN_2D]", arrays_source)
        self.assertIn("tt[LEN_2D][LEN_2D]", arrays_source)
        self.assertIn("xx = x;", arrays_source)

    def test_generated_runtime_exports_minimal_test_helpers(self):
        runtime_source = (REPO_ROOT / "emulator" / "run" / "common" / "tsvc_runtime.c").read_text(encoding="utf-8")

        self.assertIn("__attribute__((weak)) real_t test(real_t *A)", runtime_source)
        self.assertIn("__attribute__((weak)) real_t f(real_t a, real_t b)", runtime_source)
        self.assertIn("for (int i = 0; i < 4; i++)", runtime_source)
        self.assertIn("sum += A[i];", runtime_source)
        self.assertIn("return a * b;", runtime_source)


if __name__ == "__main__":
    unittest.main()
