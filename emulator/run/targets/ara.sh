TARGET_ARCH="rv64gcv"
TARGET_ABI="lp64d"
TARGET_CC="clang"
TARGET_CC_FLAGS="--target=riscv64-unknown-elf"
TARGET_CRT="crt/crt_rv64.S"
TARGET_LD="link/link_rv64.ld"
TARGET_SIM="${ARA_SIM:-${RVV_ROOT}/chipyard/sims/verilator/simulator-chipyard.harness-V4096Ara2LaneRocketConfig}"
TARGET_SIM_ARGS="+permissive +max_core_cycles=100000000 +permissive-off"
TARGET_VLEN=4096
