# OpenC910 target configuration
# NOTE: C910 uses T-Head's custom vector extension (not standard RVV)
# This target runs as scalar baseline for comparison

TARGET_ARCH="rv64gc"
TARGET_ABI="lp64d"
TARGET_CC="clang"
TARGET_CC_FLAGS="--target=riscv64-unknown-elf"
TARGET_CRT="crt/crt_c910.S"
TARGET_LD="link/link_c910.ld"
TARGET_SIM="${C910_SIM:-${RVV_ROOT}/openc910/smart_run/work/obj_dir/Vtop}"
TARGET_SIM_ARGS=""
TARGET_VLEN=0
TARGET_NEEDS_PAT=1
TARGET_C910_HOME="${C910_HOME:-${RVV_ROOT}/openc910}"
