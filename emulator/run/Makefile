KERNEL ?= s271
LMUL ?= 1
LEN_1D ?= 1000

RVV_ROOT ?= $(realpath ../..)
SPIKE ?= $(RVV_ROOT)/chipyard/.conda-env/riscv-tools/bin/spike
SATURN_SIM ?= $(RVV_ROOT)/chipyard/sims/verilator/simulator-chipyard.harness-REFV512D128RocketConfig

CC = clang
CFLAGS = --target=riscv64-unknown-elf -march=rv64gcv -mabi=lp64d
CFLAGS += -O3 -static -nostdlib -mcmodel=medany -fuse-ld=lld
CFLAGS += -fno-builtin -fno-common
CFLAGS += -DLEN_1D=$(LEN_1D)
CFLAGS += -mllvm -riscv-v-register-bit-width-lmul=$(LMUL)
CFLAGS += -Icommon

SRCS = crt.S common/arrays.c common/harness.c src/$(KERNEL).c
OUT = out
ELF = $(OUT)/$(KERNEL)_lmul$(LMUL).elf

.PHONY: all build spike saturn asm clean

all: build

$(OUT):
	@mkdir -p $(OUT)

build: | $(OUT)
	$(CC) $(CFLAGS) -Tlink.ld $(SRCS) -o $(ELF)
	@echo "Built: $(ELF)"

spike: build
	$(SPIKE) --isa=rv64gcv_zba_zbb -m0x80000000:0x10000000 $(ELF)

saturn: build
	$(SATURN_SIM) +permissive +max_core_cycles=100000000 +permissive-off $(ELF)

asm: | $(OUT)
	$(CC) $(CFLAGS) -S -o $(OUT)/$(KERNEL)_lmul$(LMUL).s src/$(KERNEL).c
	@grep "vsetvli" $(OUT)/$(KERNEL)_lmul$(LMUL).s | head -5

clean:
	rm -rf $(OUT)
