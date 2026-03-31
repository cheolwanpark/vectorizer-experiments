#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEM5_DIR="${GEM5_DIR:-${ROOT_DIR}/gem5}"
NPROC="${NPROC:-$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)}"
DEFAULT_JOBS=$((NPROC / 2))
if [ "${DEFAULT_JOBS}" -lt 1 ]; then DEFAULT_JOBS=1; fi
JOBS="${JOBS:-${DEFAULT_JOBS}}"
DRY_RUN=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        -j|--jobs)
            if [ "$#" -lt 2 ]; then
                echo "missing value for $1" >&2
                exit 2
            fi
            JOBS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [ ! -d "${GEM5_DIR}" ]; then
    echo "gem5 directory not found: ${GEM5_DIR}" >&2
    exit 1
fi

if [ "${DRY_RUN}" -eq 1 ]; then
    printf '# cwd: %s\n' "${GEM5_DIR}"
    if command -v mold >/dev/null 2>&1; then
        printf '%q ' scons "-j${JOBS}" build/RISCV/gem5.opt 'LINKFLAGS=-fuse-ld=mold' 'CXXFLAGS=-fuse-ld=mold'
    else
        printf '%q ' scons "-j${JOBS}" build/RISCV/gem5.opt
    fi
    printf '\n'
    exit 0
fi

if [ -f "${ROOT_DIR}/env.sh" ]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/env.sh" 2>/dev/null || true
fi

python3 -m pip install -U scons pyyaml >/dev/null
if [ -f "${GEM5_DIR}/requirements.txt" ]; then
    python3 -m pip install -r "${GEM5_DIR}/requirements.txt" >/dev/null
fi

LINKER_FLAGS=""
if command -v mold >/dev/null 2>&1; then
    LINKER_FLAGS="-fuse-ld=mold"
fi

cmd=(scons "-j${JOBS}" build/RISCV/gem5.opt)
if [ -n "${LINKER_FLAGS}" ]; then
    cmd+=("LINKFLAGS=${LINKER_FLAGS}" "CXXFLAGS=${LINKER_FLAGS}")
fi

cd "${GEM5_DIR}"
"${cmd[@]}"
