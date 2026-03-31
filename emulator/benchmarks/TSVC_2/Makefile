
COMPILER=GNU

ifndef COMPILER
$(error No compiler specified!)
endif

SRC_DIR=./src
OUT_ROOT?=$(abspath ..)/tsvc2_build

all:
	@$(MAKE) -C $(SRC_DIR) COMPILER=$(COMPILER) OUT_ROOT=$(OUT_ROOT)                NO_OMP=1 SUFFIX=_default
	@$(MAKE) -C $(SRC_DIR) COMPILER=$(COMPILER) OUT_ROOT=$(OUT_ROOT) FAST_MATH=1    NO_OMP=1 SUFFIX=_relaxed
	@$(MAKE) -C $(SRC_DIR) COMPILER=$(COMPILER) OUT_ROOT=$(OUT_ROOT) PRECISE_MATH=1 NO_OMP=1 SUFFIX=_precise

.PHONY: clean
clean:
	$(MAKE) -C $(SRC_DIR) COMPILER=$(COMPILER) OUT_ROOT=$(OUT_ROOT) clean
