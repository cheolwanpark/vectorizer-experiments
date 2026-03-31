export RVV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Source Nix if available (needed for T1 builds)

export USER="${USER:-$(whoami 2>/dev/null || echo root)}"
for _nix_profile in /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh \
                    "${HOME}/.nix-profile/etc/profile.d/nix.sh"; do
    if [ -f "${_nix_profile}" ]; then
        . "${_nix_profile}" 2>/dev/null
        break
    fi
done
unset _nix_profile

export LLVM_BUILD_DIR=$RVV_ROOT/llvm-build
export LLVM_BIN_DIR=$LLVM_BUILD_DIR/bin
export LLVM_DIR=$RVV_ROOT/llvm-project/llvm

export GEM5_DIR=$RVV_ROOT/gem5
export CY_DIR=$RVV_ROOT/chipyard
export CHIPYARD_DIR=$RVV_ROOT/chipyard
export PATCH_DIR=$RVV_ROOT/patches
# export XS_DIR=$RVV_ROOT/simulators/xiangshan

export TSVC_DIR=$RVV_ROOT/benchmarks/TSVC_2
export VERILATOR_DIR=$CHIPYARD_DIR/sims/verilator

export RISCV_TOOLS_PREFIX=$CHIPYARD_DIR/.conda-env/riscv-tools
export RISCV=$RISCV_TOOLS_PREFIX
export PATH=$LLVM_BIN_DIR:$CHIPYARD_DIR/.conda-env/bin:$RISCV_TOOLS_PREFIX/bin:$PATH
export LD_LIBRARY_PATH=$RISCV_TOOLS_PREFIX/lib:${LD_LIBRARY_PATH:-}

export SPIKE=$RISCV_TOOLS_PREFIX/bin/spike
export SATURN_SIM=$VERILATOR_DIR/simulator-chipyard.harness-REFV512D128RocketConfig
export ARA_SIM=$VERILATOR_DIR/simulator-chipyard.harness-V4096Ara2LaneRocketConfig

export NEMU_HOME=$RVV_ROOT/third-party/NEMU
export AM_HOME=$RVV_ROOT/third-party/nexus-am
export NOOP_HOME=$RVV_ROOT/XiangShan

# Vicuna (requires Verilator 4.210+)
export VICUNA_DIR=$RVV_ROOT/vicuna
export VICUNA_SIM=$RVV_ROOT/artifacts/vicuna-sim-512

# Activate conda if available (skip in non-interactive scripts)
if command -v conda &>/dev/null && [ -z "${CONDA_PREFIX:-}" ]; then
    conda activate $CHIPYARD_DIR/.conda-env 2>/dev/null || true
fi
