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
CONCURRENCY ?= 5
VFS_DB ?= artifacts/vfs.db
EMULATE_DB ?=
PLOT_OUTPUT_HTML ?=

BENCH := $(firstword $(filter s%,$(MAKECMDGOALS)))

.PHONY: help emulate emulate-all vplan-explain
.PHONY: vplan-explain-all plot-results FORCE

help:
	@echo "Targets:"
	@echo "  make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan"
	@echo "  make emulate-all [IMAGE=...] [LEN=4096] [LMUL=1] [TIMEOUT=120] [ARCH=RVV] [VLEN=128] [LLVM_CUSTOM=/path/to/llvm-or-bin] [CONCURRENCY=5] [VFS_DB=artifacts/vfs.db]"
	@echo "  make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC] [LEN=4096] [LMUL=1] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain] [VERBOSE=1]"
	@echo "  make vplan-explain-all [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC] [LEN=4096] [LMUL=1] [VLEN=128] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VPLAN_LOG_ROOT=artifacts/vplan-explain] [VFS_DB=artifacts/vfs.db]"
	@echo "  make plot-results [VFS_DB=artifacts/vfs.db] [EMULATE_DB=artifacts/emulate-result-YYYYMMDDHHMM.sqlite] [PLOT_OUTPUT_HTML=artifacts/plots/report.html]"

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
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--output-root "$(VPLAN_LOG_ROOT)" \
		--db-path "$(VFS_DB)"

plot-results:
	@$(UV) run python scripts/plot_results.py --vfs-db "$(VFS_DB)" $(if $(strip $(EMULATE_DB)),--emulate-db "$(EMULATE_DB)",) $(if $(strip $(PLOT_OUTPUT_HTML)),--output-html "$(PLOT_OUTPUT_HTML)",)

s%:
	@:
