
include ../makefiles/Makefile.defs

OUT_ROOT ?= ../../tsvc2_build
OUT_ROOT := $(abspath $(OUT_ROOT))
OBJ_DIR := $(OUT_ROOT)/obj/$(COMPILER)
BIN_DIR := $(OUT_ROOT)/bin/$(COMPILER)

COMMON_FILES=$(OBJ_DIR)/dummy.o $(OBJ_DIR)/common.o $(OBJ_DIR)/data.o

LOOPS_DIR := loops
LOOPS := $(notdir $(basename $(wildcard $(LOOPS_DIR)/*.c)))
LOOP_OBJ_DIR := $(OBJ_DIR)/$(LOOPS_DIR)
LOOP_BIN_DIR := $(BIN_DIR)/$(LOOPS_DIR)
LOOP_BINARIES := $(patsubst %, $(LOOP_BIN_DIR)/%, $(LOOPS))
LOOP_COMMON_FILES := $(COMMON_FILES) $(OBJ_DIR)/single_runner.o

libs=-lm

all : $(BIN_DIR)/tsvc_vec $(BIN_DIR)/tsvc_novec

loops : $(LOOP_BINARIES)

loop-% : $(LOOP_BIN_DIR)/%
	@:

$(BIN_DIR)/tsvc_% : $(OBJ_DIR)/tsvc_%.o $(COMMON_FILES)
	@mkdir -p $(BIN_DIR)
	$(CC) $^ $(libs) -o $@$(SUFFIX)

$(OBJ_DIR)/%_novec.o:%.c .FORCE
	@mkdir -p $(OBJ_DIR)
	$(CC) $(flags) $(novecflags) -c -o $@ $<

$(OBJ_DIR)/%_vec.o:%.c .FORCE
	@mkdir -p $(OBJ_DIR)
	$(CC) $(flags) $(vecflags) -c -o $@ $<

# Compiled with IEEE math flags to make initialisation/checksum calculations more reproducable
# Be wary that PGI doesn't respect IEEE properly with vectorisation
$(OBJ_DIR)/%.o:%.c .FORCE
	@mkdir -p $(OBJ_DIR)
	$(CC) $(flags) $(vecflags) $(ieee_math_flags) -c -o $@ $<

$(LOOP_BIN_DIR)/% : $(LOOP_OBJ_DIR)/%.o $(LOOP_COMMON_FILES)
	@mkdir -p $(LOOP_BIN_DIR)
	$(CC) $^ $(libs) -o $@$(SUFFIX)

$(LOOP_OBJ_DIR)/%.o:$(LOOPS_DIR)/%.c .FORCE
	@mkdir -p $(LOOP_OBJ_DIR)
	$(CC) $(flags) $(vecflags) $(ieee_math_flags) -c -o $@ $<

.PHONY: .FORCE clean loops loop-%
.FORCE:
	@true

clean :
	rm -rf $(OBJ_DIR)
