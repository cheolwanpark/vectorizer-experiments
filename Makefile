PYTHON ?= python3
UV ?= uv
IMAGE ?= vplan-cost-measure:latest
PLATFORM ?= linux/amd64
DOCKER ?= docker
LEN ?= 4096
LMUL ?= 1
USE_VF ?=
TIMEOUT ?= 120
LOG_ROOT ?= artifacts/emulate
ARCH ?= RVV
VLEN ?= 128
VF_USE ?=
LLVM_CUSTOM ?=
VPLAN_LOG_ROOT ?= artifacts/vplan-explain
VERBOSE ?= 0
CONCURRENCY ?= 1
_VFS_DB_SUFFIX := $(if $(filter INTEL,$(ARCH)),intel,$(if $(filter RVV,$(ARCH)),rvv,$(shell echo '$(ARCH)' | tr A-Z a-z)))
VFS_DB ?= artifacts/vfs-$(_VFS_DB_SUFFIX).db
RESULT_DB ?=
PLOT_VFS_DB ?=
PLOT_OUTPUT_HTML ?=
X86_MARCH ?= emeraldrapids
PROFILE_LOG_ROOT ?= artifacts/profile
PROFILE_WARMUP ?= 3
PROFILE_REPEAT ?= 10
PLOT_CMP_EMULATE_DB ?= $(lastword $(sort $(wildcard artifacts/emulate-result-*.sqlite)))
PLOT_CMP_PROFILE_DB ?= $(lastword $(sort $(wildcard artifacts/profile-result-*.sqlite)))
PLOT_CMP_EMULATE_VFS_DB ?=
PLOT_CMP_PROFILE_VFS_DB ?=
PLOT_CMP_OUTPUT_DIR ?= artifacts/plots
PLOT_CMP_PREFIX ?= rvv-intel-kernel
MICROBENCH_DB ?= artifacts/microbench.sqlite
MICROBENCH_LOG_ROOT ?= artifacts/microbench
MICROBENCH_CASE ?= all
MICROBENCH_VARIANT ?= all
DLMUL_BENCH_DB ?= artifacts/dlmul-bench.sqlite
DLMUL_BENCH_LOG_ROOT ?= artifacts/dlmul-bench
DLMUL_BENCH_CASE ?= all
DLMUL_BENCH_VARIANT ?= all

# --- RVV precise cost model flags (RISCV TTI) ---
PRECISE_MEM_COST ?=
GATHER_SCATTER_OVERHEAD ?=
STRIDED_MEM_OVERHEAD ?=

# Build matching clang/opt flags strings from the above variables
_CLANG_MLLVM_FLAGS :=
_OPT_FLAGS :=
ifneq ($(PRECISE_MEM_COST),)
_CLANG_MLLVM_FLAGS += -mllvm -precise-mem-cost
_OPT_FLAGS += -precise-mem-cost
endif
ifneq ($(GATHER_SCATTER_OVERHEAD),)
_CLANG_MLLVM_FLAGS += -mllvm -gather-scatter-overhead=$(GATHER_SCATTER_OVERHEAD)
_OPT_FLAGS += -gather-scatter-overhead=$(GATHER_SCATTER_OVERHEAD)
endif
ifneq ($(STRIDED_MEM_OVERHEAD),)
_CLANG_MLLVM_FLAGS += -mllvm -strided-mem-overhead=$(STRIDED_MEM_OVERHEAD)
_OPT_FLAGS += -strided-mem-overhead=$(STRIDED_MEM_OVERHEAD)
endif
_EXTRA_CFLAGS_ARG = $(if $(strip $(_CLANG_MLLVM_FLAGS)),--extra-cflags='$(strip $(_CLANG_MLLVM_FLAGS))',)
_EXTRA_OPT_FLAGS_ARG = $(if $(strip $(_OPT_FLAGS)),--extra-opt-flags='$(strip $(_OPT_FLAGS))',)

BENCH := $(firstword $(filter s%,$(MAKECMDGOALS)))
ASM_SOURCE := $(firstword $(filter %.s %.S,$(MAKECMDGOALS)))

.PHONY: help emulate emulate-asm emulate-all vplan-explain dlmul-microbench dlmul-bench
.PHONY: vplan-explain-all plot-results plot-results-cmp profile profile-all FORCE

help:
	@echo ""
	@echo "=== VPlan Cost Measure ==="
	@echo ""
	@echo "TARGETS:"
	@echo ""
	@echo "  emulate sXXX          Run one kernel on XiangShan emulator"
	@echo "  emulate-asm xxx.s     Run one assembly kernel on XiangShan emulator"
	@echo "  emulate-all           Run all kernels on emulator (uses VFS_DB)"
	@echo "  vplan-explain sXXX    Generate VPlan cost explanation for one kernel"
	@echo "  vplan-explain-all     Generate VPlan explanations for all kernels"
	@echo "  profile sXXX          Profile one kernel natively on x86"
	@echo "  profile-all           Profile all kernels on x86 (uses VFS_DB)"
	@echo "  plot-results          Plot results from a single result DB"
	@echo "  plot-results-cmp      Compare emulate vs profile results"
	@echo "  dlmul-microbench      Run C-based dynamic LMUL microbench suite (MB1-MB11) on XiangShan"
	@echo "  dlmul-bench           Run C-based dynamic LMUL default workload bench suite on XiangShan"
	@echo ""
	@echo "COMMON OPTIONS:"
	@echo ""
	@echo "  LEN=4096              Array length (LEN_1D)"
	@echo "  LMUL=1                RISC-V LMUL value"
	@echo "  ARCH=RVV|MAC|INTEL    Target architecture"
	@echo "  VLEN=128              RVV vector length in bits"
	@echo "  IMAGE=...             Docker image tag"
	@echo "  LLVM_CUSTOM=...       Path to custom LLVM build/bin directory"
	@echo "  X86_MARCH=emeraldrapids  x86 -march value"
	@echo "  CONCURRENCY=1         Parallel job count (*-all targets and dlmul-microbench)"
	@echo "  VERBOSE=1             Enable verbose output (vplan-explain)"
	@echo ""
	@echo "RVV COST MODEL OPTIONS (require LLVM_CUSTOM with patched LLVM):"
	@echo ""
	@echo "  PRECISE_MEM_COST=1    Enable detailed gather/scatter/strided cost model"
	@echo "                        Passes to clang: -mllvm -precise-mem-cost"
	@echo "                        Passes to opt:   -precise-mem-cost"
	@echo "  GATHER_SCATTER_OVERHEAD=N"
	@echo "                        Override gather/scatter overhead multiplier (default: 2)"
	@echo "                        Passes to clang: -mllvm -gather-scatter-overhead=N"
	@echo "                        Passes to opt:   -gather-scatter-overhead=N"
	@echo "  STRIDED_MEM_OVERHEAD=N"
	@echo "                        Override strided memory overhead multiplier (default: 1)"
	@echo "                        Passes to clang: -mllvm -strided-mem-overhead=N"
	@echo "                        Passes to opt:   -strided-mem-overhead=N"
	@echo ""
	@echo "EMULATE OPTIONS:"
	@echo ""
	@echo "  USE_VF='fixed:4'      Force vectorization factor"
	@echo "  TIMEOUT=120           Simulation timeout in seconds"
	@echo "  LOG_ROOT=artifacts/emulate  Output directory"
	@echo ""
	@echo "PROFILE OPTIONS:"
	@echo ""
	@echo "  PROFILE_WARMUP=3      Warmup iterations"
	@echo "  PROFILE_REPEAT=10     Timed iterations"
	@echo "  PROFILE_LOG_ROOT=artifacts/profile  Output directory"
	@echo ""
	@echo "PLOT OPTIONS:"
	@echo ""
	@echo "  RESULT_DB=...         Path to result sqlite (plot-results)"
	@echo "  PLOT_VFS_DB=...       VFS DB for annotations"
	@echo "  PLOT_OUTPUT_HTML=...  Output HTML path"
	@echo "  PLOT_CMP_EMULATE_DB=... / PLOT_CMP_PROFILE_DB=...  (plot-results-cmp)"
	@echo "  PLOT_CMP_OUTPUT_DIR=artifacts/plots"
	@echo "  PLOT_CMP_PREFIX=rvv-intel-kernel"
	@echo ""
	@echo "MICROBENCH OPTIONS:"
	@echo ""
	@echo "  MICROBENCH_DB=artifacts/microbench.sqlite   Output SQLite path"
	@echo "  MICROBENCH_LOG_ROOT=artifacts/microbench    Output directory"
	@echo "  MICROBENCH_CASE=all                         Case filter (e.g. mb1-switch)"
	@echo "  MICROBENCH_VARIANT=all                      Variant filter (e.g. m8_to_m1)"
	@echo "  DLMUL_BENCH_DB=artifacts/dlmul-bench.sqlite   Output SQLite path"
	@echo "  DLMUL_BENCH_LOG_ROOT=artifacts/dlmul-bench    Output directory"
	@echo "  DLMUL_BENCH_CASE=all                          Case filter (e.g. db1)"
	@echo "  DLMUL_BENCH_VARIANT=all                       Variant filter (e.g. dyn_m4_m2_m4)"
	@echo ""
	@echo "EXAMPLES:"
	@echo ""
	@echo "  make emulate s2101 LMUL=2"
	@echo "  make emulate-asm emulator/run/out/s111_xiangshan_lmul1.s"
	@echo "  make emulate-all LLVM_CUSTOM=llvm-project/build/bin PRECISE_MEM_COST=1"
	@echo "  make vplan-explain s4112 ARCH=RVV PRECISE_MEM_COST=1 GATHER_SCATTER_OVERHEAD=3"
	@echo "  make profile-all CONCURRENCY=4 X86_MARCH=sapphirerapids"
	@echo "  make dlmul-microbench MICROBENCH_CASE=mb4-two-phase MICROBENCH_VARIANT=m8_to_m1"
	@echo "  make dlmul-bench DLMUL_BENCH_CASE=db1 DLMUL_BENCH_VARIANT=all"
	@echo ""

emulate:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/emulate.py --bench "$(BENCH)" --image "$(IMAGE)" --len "$(LEN)" --lmul "$(LMUL)" $(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) --timeout "$(TIMEOUT)" --log-root "$(LOG_ROOT)" $(_EXTRA_CFLAGS_ARG) $(_EXTRA_OPT_FLAGS_ARG)

emulate-asm:
	@if [ -z "$(ASM_SOURCE)" ]; then \
		echo "usage: make emulate-asm xxx.s [IMAGE=...] [LEN=4096] [LMUL=1] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/emulate.py --source "$(ASM_SOURCE)" --image "$(IMAGE)" --len "$(LEN)" --lmul "$(LMUL)" $(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) --timeout "$(TIMEOUT)" --log-root "$(LOG_ROOT)" $(_EXTRA_CFLAGS_ARG) $(_EXTRA_OPT_FLAGS_ARG)

emulate-all: $(VFS_DB)
	@$(PYTHON) scripts/emulate_all.py \
		--image "$(IMAGE)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		--timeout "$(TIMEOUT)" \
		--log-root "$(LOG_ROOT)" \
		--arch "$(ARCH)" \
		--vlen "$(VLEN)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--concurrency "$(CONCURRENCY)" \
		--vfs-db "$(VFS_DB)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

vplan-explain:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC] [LEN=4096] [LMUL=1] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain] [VERBOSE=1]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/vplan_explain.py \
		--bench "$(BENCH)" \
		--image "$(IMAGE)" \
		--platform "$(PLATFORM)" \
		--arch "$(ARCH)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		--vlen "$(VLEN)" \
		--x86-march "$(X86_MARCH)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		$(if $(strip $(VF_USE)),--vf-use "$(VF_USE)",) \
		$(if $(filter 1 true TRUE yes YES,$(VERBOSE)),--verbose,) \
		--output-root "$(VPLAN_LOG_ROOT)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

$(VFS_DB):
	@$(PYTHON) scripts/vplan_explain_all.py \
		--image "$(IMAGE)" \
		--platform "$(PLATFORM)" \
		--arch "$(ARCH)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		--vlen "$(VLEN)" \
		--x86-march "$(X86_MARCH)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--output-root "$(VPLAN_LOG_ROOT)" \
		--db-path "$(VFS_DB)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

FORCE:

vplan-explain-all: FORCE
	@$(PYTHON) scripts/vplan_explain_all.py \
		--image "$(IMAGE)" \
		--platform "$(PLATFORM)" \
		--arch "$(ARCH)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		--vlen "$(VLEN)" \
		--x86-march "$(X86_MARCH)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--output-root "$(VPLAN_LOG_ROOT)" \
		--db-path "$(VFS_DB)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

profile:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make profile sXXX [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [LLVM_CUSTOM=...] [X86_MARCH=emeraldrapids]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/profile.py \
		--bench "$(BENCH)" \
		--image "$(IMAGE)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		$(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--x86-march "$(X86_MARCH)" \
		--warmup "$(PROFILE_WARMUP)" \
		--repeat "$(PROFILE_REPEAT)" \
		--log-root "$(PROFILE_LOG_ROOT)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

profile-all: $(VFS_DB)
	@$(PYTHON) scripts/profile_all.py \
		--image "$(IMAGE)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--x86-march "$(X86_MARCH)" \
		--warmup "$(PROFILE_WARMUP)" \
		--repeat "$(PROFILE_REPEAT)" \
		--log-root "$(PROFILE_LOG_ROOT)" \
		--concurrency "$(CONCURRENCY)" \
		--vfs-db "$(VFS_DB)" \
		$(_EXTRA_CFLAGS_ARG) \
		$(_EXTRA_OPT_FLAGS_ARG)

dlmul-microbench:
	@$(PYTHON) scripts/dlmul_microbench.py \
		--image "$(IMAGE)" \
		--db-path "$(MICROBENCH_DB)" \
		--log-root "$(MICROBENCH_LOG_ROOT)" \
		--case "$(MICROBENCH_CASE)" \
		--variant "$(MICROBENCH_VARIANT)" \
		--timeout "$(TIMEOUT)" \
		--concurrency "$(CONCURRENCY)"

dlmul-bench:
	@$(PYTHON) scripts/dlmul_bench.py \
		--image "$(IMAGE)" \
		--db-path "$(DLMUL_BENCH_DB)" \
		--log-root "$(DLMUL_BENCH_LOG_ROOT)" \
		--case "$(DLMUL_BENCH_CASE)" \
		--variant "$(DLMUL_BENCH_VARIANT)" \
		--timeout "$(TIMEOUT)" \
		--concurrency "$(CONCURRENCY)"

plot-results:
	@if [ -z "$(RESULT_DB)" ]; then \
		echo "usage: make plot-results RESULT_DB=artifacts/{emulate,profile}-result-YYYYMMDDHHMM.sqlite [PLOT_VFS_DB=...] [PLOT_OUTPUT_HTML=...]" >&2; \
		exit 2; \
	fi
	@$(UV) run python scripts/plot_results.py --result-db "$(RESULT_DB)" $(if $(strip $(PLOT_VFS_DB)),--vfs-db "$(PLOT_VFS_DB)",) $(if $(strip $(PLOT_OUTPUT_HTML)),--output-html "$(PLOT_OUTPUT_HTML)",)

plot-results-cmp:
	@if [ -z "$(PLOT_CMP_EMULATE_DB)" ] || [ -z "$(PLOT_CMP_PROFILE_DB)" ]; then \
		echo "usage: make plot-results-cmp [PLOT_CMP_EMULATE_DB=artifacts/emulate-result-*.sqlite(latest)] [PLOT_CMP_PROFILE_DB=artifacts/profile-result-*.sqlite(latest)] [PLOT_CMP_{EMULATE,PROFILE}_VFS_DB=...] [PLOT_CMP_OUTPUT_DIR=artifacts/plots] [PLOT_CMP_PREFIX=rvv-intel-kernel]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/plot_results_cmp.py \
		--emulate-db "$(PLOT_CMP_EMULATE_DB)" \
		--profile-db "$(PLOT_CMP_PROFILE_DB)" \
		$(if $(strip $(PLOT_CMP_EMULATE_VFS_DB)),--emulate-vfs-db "$(PLOT_CMP_EMULATE_VFS_DB)",) \
		$(if $(strip $(PLOT_CMP_PROFILE_VFS_DB)),--profile-vfs-db "$(PLOT_CMP_PROFILE_VFS_DB)",) \
		--output-dir "$(PLOT_CMP_OUTPUT_DIR)" \
		--prefix "$(PLOT_CMP_PREFIX)"

s%:
	@:

%.s:
	@:

%.S:
	@:
