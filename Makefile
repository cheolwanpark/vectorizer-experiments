PYTHON ?= python3
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
CONCURRENCY ?= 10
SAMPLES ?= 10

BENCH := $(firstword $(filter s%,$(MAKECMDGOALS)))

.PHONY: help emulate emulate-all vplan-explain

help:
	@echo "Targets:"
	@echo "  make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan"
	@echo "  make emulate-all [IMAGE=...] [LEN=4096] [LMUL=1] [TIMEOUT=120] [ARCH=RVV] [VLEN=128] [LLVM_CUSTOM=/path/to/llvm-or-bin] [CONCURRENCY=10] [SAMPLES=10]"
	@echo "  make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain]"

emulate:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF='fixed:4'] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]   # XiangShan" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/emulate.py --bench "$(BENCH)" --image "$(IMAGE)" --len "$(LEN)" --lmul "$(LMUL)" $(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) --timeout "$(TIMEOUT)" --log-root "$(LOG_ROOT)"

emulate-all:
	@$(PYTHON) scripts/emulate_all.py \
		--image "$(IMAGE)" \
		--len "$(LEN)" \
		--lmul "$(LMUL)" \
		--timeout "$(TIMEOUT)" \
		--log-root "$(LOG_ROOT)" \
		--vplan-log-root "$(VPLAN_LOG_ROOT)" \
		--arch "$(ARCH)" \
		--vlen "$(VLEN)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		--concurrency "$(CONCURRENCY)" \
		--samples "$(SAMPLES)"

vplan-explain:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [ARCH=RVV|MAC] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/vplan_explain.py \
		--bench "$(BENCH)" \
		--image "$(IMAGE)" \
		--platform "$(PLATFORM)" \
		--arch "$(ARCH)" \
		--vlen "$(VLEN)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		$(if $(strip $(VF_USE)),--vf-use "$(VF_USE)",) \
		--output-root "$(VPLAN_LOG_ROOT)"

s%:
	@:
