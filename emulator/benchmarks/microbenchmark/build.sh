#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/../.. && pwd)"
OUT_DIR="${ROOT}/benchmarks/microbenchmark/out"
mkdir -p "${OUT_DIR}"

CLANG="${ROOT}/llvm-build/bin/clang"
SYSROOT="${ROOT}/riscv-tools-install/riscv64-unknown-elf"
TOOLCHAIN="${ROOT}/riscv-tools-install"

common_flags=(
  -std=c11
  -target riscv64-unknown-elf
  -march=rv64gcv
  -mabi=lp64d
  -mcmodel=medany
  --sysroot="${SYSROOT}"
  --gcc-toolchain="${TOOLCHAIN}"
  -ffreestanding -nostdlib -static
  -O3 -fstrict-aliasing -ffp-contract=fast
  -fno-vectorize -fno-slp-vectorize
  -I"${ROOT}/benchmarks/microbenchmark"
  -I"${ROOT}/benchmarks/microbenchmark/riscv-test-env"
  -I"${ROOT}/benchmarks/microbenchmark/riscv-test-env/p"
)
link_flags=(
  -fuse-ld=lld
  -T "${ROOT}/benchmarks/microbenchmark/bare.ld"
)

echo "Building ${OUT_DIR}/swap_halves.elf"
"${CLANG}" \
  "${common_flags[@]}" \
  "${link_flags[@]}" \
  "${ROOT}/benchmarks/microbenchmark/start.S" \
  "${ROOT}/benchmarks/microbenchmark/swap_halves.c" \
  -o "${OUT_DIR}/swap_halves.elf"

echo "Generating ${OUT_DIR}/swap_halves.s"
"${CLANG}" \
  "${common_flags[@]}" \
  -S \
  "${ROOT}/benchmarks/microbenchmark/swap_halves.c" \
  -o "${OUT_DIR}/swap_halves.s"

echo "Generating ${OUT_DIR}/swap_halves.opt.ll"
"${CLANG}" \
  "${common_flags[@]}" \
  -S -emit-llvm \
  "${ROOT}/benchmarks/microbenchmark/swap_halves.c" \
  -o "${OUT_DIR}/swap_halves.opt.ll"

echo "Building ${OUT_DIR}/swap_halves_rvt.elf (riscv-test env)"
"${CLANG}" \
  "${common_flags[@]}" \
  -DEXTERN_TOTOHOST=1 \
  -DMEASURE_ITERS=5 -DWARMUP_ITERS=1 \
  -T "${ROOT}/benchmarks/microbenchmark/rvt_link.ld" \
  -fuse-ld=lld \
  "${ROOT}/benchmarks/microbenchmark/start_rvt.S" \
  "${ROOT}/benchmarks/microbenchmark/swap_halves.c" \
  -o "${OUT_DIR}/swap_halves_rvt.elf"
