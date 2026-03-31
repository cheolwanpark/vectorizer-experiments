# Vicuna target configuration
# ISA: rv32im_zve32x (integer-only vector extension)
# VLEN: 512 bits (default)
# Memory map: Boot 0x0-0x2000, RAM 0x2000-0x40000
# Termination: jr x0 (jump to address 0)
# UART: 0xFF000000

TARGET_ARCH="rv32im_zve32x"
TARGET_ABI="ilp32"
TARGET_CC="clang"
TARGET_CC_FLAGS="--target=riscv32-unknown-elf -menable-experimental-extensions"
TARGET_CRT="crt/crt_vicuna.S"
TARGET_LD="link/link_vicuna.ld"
TARGET_SIM="${VICUNA_SIM:-${RVV_ROOT}/artifacts/vicuna-sim-512}"
TARGET_SIM_ARGS=""
TARGET_LOADMEM=0
TARGET_VLEN=512
TARGET_VICUNA=1
