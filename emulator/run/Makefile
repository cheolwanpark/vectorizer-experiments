KERNEL ?= s271
LMUL ?= 1
LEN_1D ?= 1000

OUT = out
ELF = $(OUT)/$(KERNEL)/$(KERNEL)_lmul$(LMUL).elf

.PHONY: all build spike saturn asm clean

all: build

$(OUT):
	@mkdir -p $(OUT)

build: | $(OUT)
	./build-workload saturn src/$(KERNEL)/manifest.yaml --lmul=$(LMUL) --len=$(LEN_1D) --output=$(ELF)
	@echo "Built: $(ELF)"

spike: build
	../run-sim.sh spike $(ELF)

saturn: build
	../run-sim.sh saturn $(ELF)

asm: | $(OUT)
	./build-workload saturn src/$(KERNEL)/manifest.yaml --lmul=$(LMUL) --len=$(LEN_1D) --asm --build-out-dir=$(OUT)

clean:
	rm -rf $(OUT)
