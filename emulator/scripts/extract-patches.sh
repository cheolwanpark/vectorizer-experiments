#!/bin/bash
#
# Extract patches from submodules
#
# Usage:
#   ./scripts/extract-patches.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
PATCH_DIR="${ROOT_DIR}/patches"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    case "${level}" in
        INFO)  echo -e "${BLUE}[INFO]${NC} $*" ;;
        OK)    echo -e "${GREEN}[OK]${NC} $*" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $*" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $*" ;;
    esac
}

extract_chipyard_patches() {
    log INFO "Extracting Chipyard patches..."

    # 1. Chipyard Verilator Makefile
    local makefile_patch="${PATCH_DIR}/chipyard-verilator-makefile.patch"
    cd "${ROOT_DIR}/chipyard"
    if git diff --quiet sims/verilator/Makefile 2>/dev/null; then
        log WARN "No changes in sims/verilator/Makefile"
    else
        git diff sims/verilator/Makefile > "${makefile_patch}"
        log OK "Created: chipyard-verilator-makefile.patch ($(wc -l < "${makefile_patch}") lines)"
    fi

    # 2. Ara outer (ara_files.f, chipyard.mk)
    local ara_outer_patch="${PATCH_DIR}/chipyard-ara-outer.patch"
    cd "${ROOT_DIR}/chipyard/generators/ara"
    if git diff --quiet -- ara_files.f chipyard.mk 2>/dev/null; then
        log WARN "No changes in ara_files.f or chipyard.mk"
    else
        git diff -- ara_files.f chipyard.mk > "${ara_outer_patch}"
        log OK "Created: chipyard-ara-outer.patch ($(wc -l < "${ara_outer_patch}") lines)"
    fi

    # 3. Ara inner (Bender.yml, Bender.lock, hardware/)
    local ara_inner_patch="${PATCH_DIR}/chipyard-ara-inner.patch"
    cd "${ROOT_DIR}/chipyard/generators/ara/ara"
    if git diff --quiet -- Bender.yml Bender.lock hardware/ 2>/dev/null; then
        log WARN "No changes in ara/ara (Bender.yml, Bender.lock, hardware/)"
    else
        git diff -- Bender.yml Bender.lock hardware/ > "${ara_inner_patch}"
        log OK "Created: chipyard-ara-inner.patch ($(wc -l < "${ara_inner_patch}") lines)"
    fi

    # 4. riscv-isa-sim
    local spike_patch="${PATCH_DIR}/riscv-isa-sim.patch"
    cd "${ROOT_DIR}/chipyard/toolchains/riscv-tools/riscv-isa-sim"
    if git diff --quiet 2>/dev/null; then
        log WARN "No changes in riscv-isa-sim"
    else
        git diff > "${spike_patch}"
        log OK "Created: riscv-isa-sim.patch ($(wc -l < "${spike_patch}") lines)"
    fi
}

extract_t1_patches() {
    log INFO "Extracting T1 patches..."

    local t1_patch="${PATCH_DIR}/t1-micro58ae.patch"
    cd "${ROOT_DIR}/t1-micro58ae"
    if git diff --quiet 2>/dev/null; then
        log WARN "No changes in t1-micro58ae"
    else
        git diff > "${t1_patch}"
        log OK "Created: t1-micro58ae.patch ($(wc -l < "${t1_patch}") lines)"
    fi
}

show_status() {
    log INFO "Current submodule status:"
    echo ""

    echo -e "${BLUE}chipyard:${NC}"
    cd "${ROOT_DIR}/chipyard" 2>/dev/null && git status --short || echo "  (not initialized)"

    echo -e "\n${BLUE}chipyard/generators/ara:${NC}"
    cd "${ROOT_DIR}/chipyard/generators/ara" 2>/dev/null && git status --short || echo "  (not initialized)"

    echo -e "\n${BLUE}chipyard/generators/ara/ara:${NC}"
    cd "${ROOT_DIR}/chipyard/generators/ara/ara" 2>/dev/null && git status --short || echo "  (not initialized)"

    echo -e "\n${BLUE}chipyard/toolchains/riscv-tools/riscv-isa-sim:${NC}"
    cd "${ROOT_DIR}/chipyard/toolchains/riscv-tools/riscv-isa-sim" 2>/dev/null && git status --short || echo "  (not initialized)"

    echo -e "\n${BLUE}t1-micro58ae:${NC}"
    cd "${ROOT_DIR}/t1-micro58ae" 2>/dev/null && git status --short || echo "  (not initialized)"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TARGETS...]

Extract patches from submodules to patches/ directory.

Targets:
    chipyard    Extract chipyard-related patches (verilator, ara, riscv-isa-sim)
    t1          Extract t1-micro58ae patches
    all         Extract all patches (default)

Options:
    --status    Show current submodule modification status
    --help      Show this help

Examples:
    $0                  # Extract all patches
    $0 chipyard         # Extract chipyard patches only
    $0 t1               # Extract t1 patches only
    $0 --status         # Show what's modified in submodules
EOF
}

main() {
    mkdir -p "${PATCH_DIR}"

    local targets=()
    local show_status_only=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --status)
                show_status_only=true
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            chipyard|t1|all)
                targets+=("$1")
                shift
                ;;
            *)
                log ERROR "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [[ "${show_status_only}" == true ]]; then
        show_status
        exit 0
    fi

    # Default: extract all
    if [[ ${#targets[@]} -eq 0 ]]; then
        targets=("all")
    fi

    log INFO "=== Extracting Patches ==="
    log INFO "Output directory: ${PATCH_DIR}"
    echo ""

    for target in "${targets[@]}"; do
        case "${target}" in
            chipyard)
                extract_chipyard_patches
                ;;
            t1)
                extract_t1_patches
                ;;
            all)
                extract_chipyard_patches
                echo ""
                extract_t1_patches
                ;;
        esac
    done

    echo ""
    log OK "=== Done ==="
    log INFO "Patches saved to: ${PATCH_DIR}/"
    ls -la "${PATCH_DIR}"/*.patch 2>/dev/null || true
}

main "$@"
