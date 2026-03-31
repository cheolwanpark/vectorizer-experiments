#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="${PATCH_DIR:-${ROOT_DIR}/patches}"

NPROC="${NPROC:-$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)}"
OPTIMAL_JOBS="${OPTIMAL_JOBS:-$((NPROC / 2))}"
if [ "${OPTIMAL_JOBS}" -lt 1 ]; then OPTIMAL_JOBS=1; fi

CHIPYARD_DIR="${CHIPYARD_DIR:-${ROOT_DIR}/chipyard}"
GEM5_DIR="${GEM5_DIR:-${ROOT_DIR}/gem5}"
LLVM_DIR="${LLVM_DIR:-${ROOT_DIR}/llvm-project/llvm}"
LLVM_BUILD_DIR="${LLVM_BUILD_DIR:-${ROOT_DIR}/llvm-build}"
XIANGSHAN_DIR="${XIANGSHAN_DIR:-${ROOT_DIR}/XiangShan}"
T1_DIR="${T1_DIR:-${ROOT_DIR}/t1-micro58ae}"

log() { printf '[%s] %s\n' "$1" "$2" >&2; }

check_cmd() {
    command -v "$1" &> /dev/null
}

SUDO="sudo"
if [ "${EUID:-0}" -eq 0 ]; then
    SUDO=""
fi

${SUDO} apt-get update
${SUDO} apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    openjdk-21-jdk \
    verilator \
    gtkwave \
    numactl \
    cmake \
    ninja-build \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libgmp-dev \
    libmpfr-dev \
    libmpc-dev \
    zlib1g-dev \
    libboost-all-dev \
    device-tree-compiler \
    libfdt-dev \
    bc \
    flex \
    bison \
    mold \
    libsqlite3-dev \
    libreadline-dev \
    libzstd-dev \
    libsdl2-dev \
    ccache \
    python3-dev

# Mill (required for XiangShan)
install_mill() {
    if check_cmd mill && mill --version >/dev/null 2>&1; then
        log INFO "Mill already installed: $(mill --version 2>&1 | head -1)"
        return 0
    fi
    # XiangShan uses .mill-version to specify the required version.
    # Install the mill-dist jar directly; it auto-selects the right version
    # from .mill-version at runtime.
    local MILL_VERSION="${MILL_VERSION:-0.12.3}"
    local MILL_URL="https://repo1.maven.org/maven2/com/lihaoyi/mill-dist/${MILL_VERSION}/mill-dist-${MILL_VERSION}.jar"
    log INFO "Installing Mill ${MILL_VERSION}..."
    curl -fsSL "${MILL_URL}" -o /usr/local/bin/mill
    chmod +x /usr/local/bin/mill
    log OK "Mill ${MILL_VERSION} installed"
}
install_mill

# Nix (required for T1)
install_nix() {
    rm -rf /homeless-shelter 2>/dev/null || true
    if check_cmd nix; then
        log INFO "Nix already installed: $(nix --version 2>&1)"
        return 0
    fi
    # Ensure $USER is set (nix profile script requires it)
    export USER="${USER:-$(whoami 2>/dev/null || echo root)}"
    # Create /nix directory (installer's sudo call may fail in containers)
    mkdir -m 0755 -p /nix && chown "$(id -u)" /nix
    # Pre-create nix.conf to disable build-users-group (needed for root/single-user)
    local NIX_CONF_DIR="/etc/nix"
    mkdir -p "${NIX_CONF_DIR}"
    tee "${NIX_CONF_DIR}/nix.conf" > /dev/null <<NIXEOF
build-users-group =
experimental-features = nix-command flakes
max-jobs = auto
cores = ${OPTIMAL_JOBS}
NIXEOF
    log INFO "Installing Nix (single-user, no daemon)..."
    curl -L https://nixos.org/nix/install | sh -s -- --no-daemon
    # Source into current shell
    for _nix_profile in /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh \
                        "${HOME}/.nix-profile/etc/profile.d/nix.sh"; do
        if [ -f "${_nix_profile}" ]; then
            . "${_nix_profile}"
            break
        fi
    done
    unset _nix_profile
    if check_cmd nix; then
        log OK "Nix installed: $(nix --version 2>&1)"
    else
        log WARN "Nix not available after install attempt (T1 builds will not work)"
    fi
}
install_nix

# Conda
ensure_conda_shell() {
    if check_cmd conda; then
        eval "$(conda shell.bash hook)"
        return 0
    fi
    return 1
}

install_conda() {
    if check_cmd conda; then
        ensure_conda_shell || true
        log INFO "Conda already installed"
        return 0
    fi

    local conda_dir="${ROOT_DIR}/conda"
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p "${conda_dir}"
    rm /tmp/miniconda.sh
    eval "$("${conda_dir}/bin/conda" shell.bash hook)"
    log OK "Conda installed"
}
install_conda


# Git
cd "${ROOT_DIR}"

submodule_update() {
    local path="$1"
    if [ "${RECURSIVE:-1}" -gt 0 ]; then
  	    git submodule update --init --recursive --jobs $(nproc) -- "${path}"
    else
	    git submodule update --init --jobs $(nproc) -- "${path}"
    fi
}

if [ "${SKIP_ROOT_SUBMODULE_UPDATE:-0}" -eq 1 ]; then
    log INFO "Skipping root git submodule update; using pre-cloned repositories"
else
    RECURSIVE=0 submodule_update chipyard
    submodule_update gem5
    RECURSIVE=0 submodule_update llvm-project
    submodule_update XiangShan
fi
# XiangShan difftest expects build dir at ./difftest/build but RTL is at ./build
ln -sfn ../build "${XIANGSHAN_DIR}/difftest/build" 2>/dev/null || true

cd "${XIANGSHAN_DIR}"
git submodule update --init --recursive -- difftest 2>/dev/null || true
cd "${XIANGSHAN_DIR}/difftest"
git apply --check "${PATCH_DIR}/xiangshan-difftest.patch" 2>/dev/null && git apply "${PATCH_DIR}/xiangshan-difftest.patch" || true
cd "${ROOT_DIR}"

if [ "${SKIP_ROOT_SUBMODULE_UPDATE:-0}" -eq 1 ]; then
    log INFO "Skipping root git submodule update for t1/NEMU/nexus-am"
else
    RECURSIVE=0 submodule_update t1-micro58ae
    RECURSIVE=0 submodule_update third-party/NEMU
    RECURSIVE=0 submodule_update third-party/nexus-am
fi

cd $CHIPYARD_DIR
git submodule update --init --recursive toolchains/riscv-tools/riscv-isa-sim
git submodule update --init --recursive generators/ara
echo "submodule_update done"

# Build NEMU reference model for XiangShan difftest
export NEMU_HOME="${ROOT_DIR}/third-party/NEMU"
export AM_HOME="${ROOT_DIR}/third-party/nexus-am"
if [ ! -f "${NEMU_HOME}/build/riscv64-nemu-interpreter-so" ]; then
    log INFO "Building NEMU reference model..."
    cd "${NEMU_HOME}"
    make riscv64-xs-kunminghu-v3-ref_defconfig
    make -j${OPTIMAL_JOBS}
    cd "${ROOT_DIR}"
    log OK "NEMU built"
fi

# Fix shallow-clone submodule issue: restore deleted files in all submodules
# This commonly happens with --depth clones where git marks files as deleted
# restore_submodule_files() {
#     local dir="$1"
#     if [ -f "${dir}/.git" ]; then
#         local deleted_count
#         deleted_count=$(git -C "${dir}" status --porcelain 2>/dev/null | grep "^D" | wc -l || echo 0)
#         if [ "${deleted_count}" -gt 0 ]; then
#             log INFO "Restoring ${deleted_count} deleted files in ${dir}"
#             git -C "${dir}" restore --staged . 2>/dev/null || true
#             git -C "${dir}" checkout . 2>/dev/null || true
#         fi
#     fi
# }

# Restore files in critical submodules
#for submod in \
    # tools/cde \
    # tools/rocket-dsp-utils \
    # tools/dsptools \
    # tools/fixedpoint \
    # tools/firrtl2 \
    # generators/rocc-acc-utils \
    #generators/rerocc \
    #generators/bar-fetchers; do
    #restore_submodule_files "${CHIPYARD_DIR}/${submod}"
#done

cd "${CHIPYARD_DIR}/toolchains/riscv-tools/riscv-isa-sim"
git apply --check "${PATCH_DIR}/riscv-isa-sim.patch" 2>/dev/null && git apply "${PATCH_DIR}/riscv-isa-sim.patch" || true

cd "${T1_DIR}"
git apply --check "${PATCH_DIR}/t1-micro58ae.patch" 2>/dev/null && git apply "${PATCH_DIR}/t1-micro58ae.patch" || true

# Install CIRCT/firtool (required for Chisel -> Verilog)
CIRCT_VERSION="${CIRCT_VERSION:-firtool-1.75.0}"
CIRCT_DIR="${ROOT_DIR}/circt"
if [ ! -x "${CIRCT_DIR}/bin/firtool" ]; then
    log INFO "Installing CIRCT ${CIRCT_VERSION}..."
    mkdir -p "${CIRCT_DIR}"
    CIRCT_URL="https://github.com/llvm/circt/releases/download/${CIRCT_VERSION}/circt-full-shared-linux-x64.tar.gz"
    curl -fsSL "${CIRCT_URL}" | tar -xzf - -C "${CIRCT_DIR}" --strip-components=1
    log OK "CIRCT installed to ${CIRCT_DIR}"
fi
export PATH="${CIRCT_DIR}/bin:${PATH}"

# Chipyard
cd "${CHIPYARD_DIR}"
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
./build-setup.sh --skip-precompile --use-lean-conda -s 10

# Apply Chipyard patches
log INFO "Applying Chipyard patches..."
cd "${CHIPYARD_DIR}/sims/verilator"
git apply --check "${PATCH_DIR}/chipyard-verilator-makefile.patch" 2>/dev/null && git apply "${PATCH_DIR}/chipyard-verilator-makefile.patch" || true

cd "${CHIPYARD_DIR}/generators/ara"
git apply --check "${PATCH_DIR}/chipyard-ara-outer.patch" 2>/dev/null && git apply "${PATCH_DIR}/chipyard-ara-outer.patch" || true

cd "${CHIPYARD_DIR}/generators/ara/ara"
git apply --check "${PATCH_DIR}/chipyard-ara-inner.patch" 2>/dev/null && git apply "${PATCH_DIR}/chipyard-ara-inner.patch" || true

# Initialize Ara dependencies via Bender
log INFO "Initializing Ara dependencies (Bender checkout)..."
cd "${CHIPYARD_DIR}/generators/ara/ara/hardware"
make checkout 2>/dev/null || true
make apply-patches 2>/dev/null || true

cd "${ROOT_DIR}"
source env.sh

# Gem5
python -m pip install -U scons pyyaml >/dev/null
python -m pip install -r "${GEM5_DIR}/requirements.txt" >/dev/null

# LLVM
rm -rf $LLVM_BUILD_DIR
LLVM_C_COMPILER="${LLVM_C_COMPILER:-$(command -v clang || command -v gcc)}"
LLVM_CXX_COMPILER="${LLVM_CXX_COMPILER:-$(command -v clang++ || command -v g++)}"
LLVM_LD_FLAGS=""
if check_cmd mold; then
    LLVM_LD_FLAGS="-fuse-ld=mold"
fi

cmake -S $LLVM_DIR -B $LLVM_BUILD_DIR -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DLLVM_ENABLE_PROJECTS="clang;lld" \
  -DLLVM_TARGETS_TO_BUILD="RISCV;host" \
  -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_DEFAULT_TARGET_TRIPLE="riscv64-unknown-linux-gnu" \
  -DLLVM_OPTIMIZED_TABLEGEN=ON \
  -DLLVM_PARALLEL_LINK_JOBS="${OPTIMAL_JOBS}" \
  -DCMAKE_C_COMPILER="${LLVM_C_COMPILER}" \
  -DCMAKE_CXX_COMPILER="${LLVM_CXX_COMPILER}" \
  -DCMAKE_EXE_LINKER_FLAGS="${LLVM_LD_FLAGS}" \
  -DCMAKE_SHARED_LINKER_FLAGS="${LLVM_LD_FLAGS}"
ninja -C $LLVM_BUILD_DIR clang lld llvm-objdump llvm-objcopy llvm-readelf llvm-nm

# Auto-append env.sh to shell rc files
_append_env_source() {
    local rc_file="$1"
    local source_line="source ${ROOT_DIR}/env.sh"
    if [ -f "${rc_file}" ]; then
        if ! grep -qF "source ${ROOT_DIR}/env.sh" "${rc_file}" 2>/dev/null; then
            printf '\n# RVV-POC environment\n%s\n' "${source_line}" >> "${rc_file}"
            log INFO "Added env.sh to ${rc_file}"
        fi
    else
        printf '# RVV-POC environment\n%s\n' "${source_line}" > "${rc_file}"
        log INFO "Created ${rc_file} with env.sh"
    fi
}

_append_env_source "${HOME}/.bashrc"
_append_env_source "${HOME}/.zshrc"

log OK "Dependencies/toolchains ready. Run ./build-sim.sh to build simulators."
