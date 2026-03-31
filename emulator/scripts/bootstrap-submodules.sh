#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

log() {
    printf '[%s] %s\n' "$1" "$2" >&2
}

path_is_nonempty_dir() {
    local path="$1"
    [ -d "${path}" ] && find "${path}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null | grep -q .
}

ensure_repo() {
    local path="$1"
    local url="$2"
    local abs_path="${ROOT_DIR}/${path}"

    mkdir -p "$(dirname "${abs_path}")"

    if git -C "${abs_path}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log INFO "Repository already present: ${path}"
        return 0
    fi

    if path_is_nonempty_dir "${abs_path}"; then
        log ERROR "Refusing to replace non-empty path: ${path}"
        exit 1
    fi

    rmdir "${abs_path}" 2>/dev/null || true
    log INFO "Cloning ${path} from ${url}"
    git clone --depth 1 "${url}" "${abs_path}"
}

main() {
    ensure_repo "chipyard" "https://github.com/ucb-bar/chipyard.git"
    ensure_repo "gem5" "https://github.com/gem5/gem5.git"
    ensure_repo "llvm-project" "https://github.com/llvm/llvm-project.git"
    ensure_repo "XiangShan" "https://github.com/OpenXiangShan/XiangShan.git"
    ensure_repo "t1-micro58ae" "https://github.com/chipsalliance/t1.git"
    ensure_repo "third-party/NEMU" "https://github.com/OpenXiangShan/NEMU.git"
    ensure_repo "third-party/nexus-am" "https://github.com/OpenXiangShan/nexus-am.git"
}

main "$@"
