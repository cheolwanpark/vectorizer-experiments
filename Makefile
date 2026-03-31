PYTHON ?= python3
IMAGE ?= vplan-cost-measure:latest
PLATFORM ?= linux/amd64
DOCKER ?= docker
LEN ?= 4096
LMUL ?= 1
USE_VF ?=
TIMEOUT ?= 120
LOG_ROOT ?= artifacts/emulate
TYPE ?= dbl
ARCH ?= RVV
VLEN ?= 128
VF_USE ?=
LLVM_CUSTOM ?=
VPLAN_LOG_ROOT ?= artifacts/vplan-explain

BENCH := $(firstword $(filter s%,$(MAKECMDGOALS)))

.PHONY: help emulate vplan-explain

help:
	@echo "Targets:"
	@echo "  make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF=4] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]"
	@echo "  make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [TYPE=dbl|flt] [ARCH=RVV|MAC] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain]"

emulate:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make emulate sXXX [IMAGE=...] [LEN=4096] [LMUL=1] [USE_VF=4] [TIMEOUT=120] [LOG_ROOT=artifacts/emulate]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/emulate.py --bench "$(BENCH)" --image "$(IMAGE)" --len "$(LEN)" --lmul "$(LMUL)" $(if $(strip $(USE_VF)),--use-vf "$(USE_VF)",) --timeout "$(TIMEOUT)" --log-root "$(LOG_ROOT)"

vplan-explain:
	@if [ -z "$(BENCH)" ]; then \
		echo "usage: make vplan-explain sXXX [IMAGE=...] [PLATFORM=linux/amd64] [TYPE=dbl|flt] [ARCH=RVV|MAC] [VLEN=128|256|512...] [LLVM_CUSTOM=/path/to/llvm-or-bin] [VF_USE='fixed:2'] [VPLAN_LOG_ROOT=artifacts/vplan-explain]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) scripts/vplan_explain.py \
		--bench "$(BENCH)" \
		--image "$(IMAGE)" \
		--platform "$(PLATFORM)" \
		--type "$(TYPE)" \
		--arch "$(ARCH)" \
		--vlen "$(VLEN)" \
		$(if $(strip $(LLVM_CUSTOM)),--llvm-custom "$(LLVM_CUSTOM)",) \
		$(if $(strip $(VF_USE)),--vf-use "$(VF_USE)",) \
		--output-root "$(VPLAN_LOG_ROOT)"

s%:
	@:
