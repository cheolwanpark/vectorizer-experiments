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
X86_MARCH ?= sapphirerapids
PROFILE_LOG_ROOT ?= artifacts/profile
PROFILE_WARMUP ?= 3
PROFILE_REPEAT ?= 10
PLOT_CMP_EMULATE_DB ?= $(lastword $(sort $(wildcard artifacts/emulate-result-*.sqlite)))
PLOT_CMP_PROFILE_DB ?= $(lastword $(sort $(wildcard artifacts/profile-result-*.sqlite)))
PLOT_CMP_EMULATE_VFS_DB ?=
PLOT_CMP_PROFILE_VFS_DB ?=
PLOT_CMP_OUTPUT_DIR ?= artifacts/plots
PLOT_CMP_PREFIX ?= rvv-intel-kernel

BENCH := $(firstword $(filter s%,$(MAKECMDGOALS)))

.PHONY: help emulate emulate-all vplan-explain
.PHONY: vplan-explain-all plot-results plot-results-cmp profile profile-all FORCE

help:
	@echo "Targets:"
	@echo "  make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan"
	@echo "  make emulate-all [IMAGE=...] [LEN=4096] [LMUL=1] [TIMEOUT=120] [ARCH=RVV|MAC|INTEL] [VLEN=128] [LLVM_CUSTOM=...] [CONCURRENCY=1] [VFS_DB=artifacts/vfs-{rvv,intel}.db]"
	@echo "  make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC|INTEL] [LEN=4096] [LMUL=1] [VLEN=128] [LLVM_CUSTOM=...] [X86_MARCH=sapphirerapids] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain] [VERBOSE=1]"
	@echo "  make vplan-explain-all [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC|INTEL] [LEN=4096] [LMUL=1] [VLEN=128] [LLVM_CUSTOM=...] [X86_MARCH=sapphirerapids] [VPLAN_LOG_ROOT=artifacts/vplan-explain] [VFS_DB=artifacts/vfs-{rvv,intel}.db]"
	@echo "  make profile sXXX [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [LLVM_CUSTOM=...] [X86_MARCH=sapphirerapids] [PROFILE_WARMUP=3] [PROFILE_REPEAT=10] [PROFILE_LOG_ROOT=artifacts/profile]"
	@echo "  make profile-all [LEN=4096] [LMUL=1] [LLVM_CUSTOM=...] [X86_MARCH=sapphirerapids] [PROFILE_WARMUP=3] [PROFILE_REPEAT=10] [CONCURRENCY=1] [VFS_DB=artifacts/vfs-{rvv,intel}.db]"
	@echo "  make plot-results RESULT_DB=artifacts/{emulate,profile}-result-YYYYMMDDHHMM.sqlite [PLOT_VFS_DB=artifacts/vfs-{rvv,intel}.db (auto)] [PLOT_OUTPUT_HTML=artifacts/plots/report.html]"
	@echo "  make plot-results-cmp [PLOT_CMP_EMULATE_DB=artifacts/emulate-result-*.sqlite(latest)] [PLOT_CMP_PROFILE_DB=artifacts/profile-result-*.sqlite(latest)] [PLOT_CMP_{EMULATE,PROFILE}_VFS_DB=...] [PLOT_CMP_OUTPUT_DIR=artifacts/plots] [PLOT_CMP_PREFIX=rvv-intel-kernel]"

emulate:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/emulate.py --bench "$(BENCH)" --image "$(IMAGE)" --len "$(LEN)" --lmul "$(LMUL)" $(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) --timeout "$(TIMEOUT)" --log-root "$(LOG_ROOT)"

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
		--vfs-db "$(VFS_DB)"

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
		--output-root "$(VPLAN_LOG_ROOT)"

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
		--db-path "$(VFS_DB)"

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
		--db-path "$(VFS_DB)"

profile:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make profile sXXX [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [LLVM_CUSTOM=...] [X86_MARCH=sapphirerapids]" >&2; \
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
		--log-root "$(PROFILE_LOG_ROOT)"

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
		--vfs-db "$(VFS_DB)"

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
