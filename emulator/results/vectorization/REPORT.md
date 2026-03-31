# RVV Vectorization Verification Report

**Date**: 2026-02-10
**Toolchain**: LLVM/Clang (custom build)
**LMUL hint**: `-mllvm -riscv-v-register-bit-width-lmul=N`
**Optimization**: `-O2 -ffast-math`

## Targets

| Target | ISA | VLEN | DLEN | Notes |
|--------|-----|------|------|-------|
| Saturn | rv64gcv | 512 | 128 | Chipyard/Verilator |
| XiangShan | rv64gcv | 128 | 128 | KunMingHu core |
| T1 (blastoise) | rv32gcv | 2048 | 256 | Nix-based build |

## 1. Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total combinations | 372 | 100% |
| Vectorized | 356 | 95.7% |
| Scalar fallback | 0 | 0% |
| Build failure (T1) | 16 | 4.3% |
| LMUL mismatch | 13 | 3.5% |

### Per-Target Breakdown

| Target | Vectorized | Scalar | Build Fail | LMUL Mismatch |
|--------|-----------|--------|------------|---------------|
| Saturn | 124/124 | 0 | 0 | 6 |
| XiangShan | 124/124 | 0 | 0 | 6 |
| T1 | 108/124 | 0 | 16 | 1 |

> **Correction (2026-02-12)**: Previous report counted 39 LMUL mismatches due to a
> detection bug in `verify_vectorization.sh`. The old elif-chain matched `m1` from
> prologue `vsetvli` (scalar init) before checking higher LMULs. Also, mixed-SEW
> kernels (e32+e64 for index ops) were falsely flagged because `e64,m2` was counted
> as an LMUL mismatch when the primary `e32` operations correctly used `m1`.
> Fixed by extracting max LMUL from `e32` vsetvli instructions only.

## 2. Per-Kernel Vectorization Status

`!` = LMUL mismatch (compiler ignored the hint), `BFAIL` = build failure

Detection method: max LMUL from `e32` vsetvli instructions only (ignores `e64` index ops and prologue scalar init).

| Kernel | Saturn (LMUL 1/2/4/8) | XiangShan (LMUL 1/2/4/8) | T1 (LMUL 1/2/4/8) |
|--------|----------------------|--------------------------|-------------------|
| s000 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s121 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s124 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s1279 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s128 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 **m4!** |
| s1281 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s131 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s1421 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s251 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s252 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s253 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s254 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s271 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s2710 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s276 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s278 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s279 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s311 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s313 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s331 | m1 m2 m4 m8 | m1 m2 m4 m8 | BFAIL BFAIL BFAIL BFAIL |
| s332 | m1 m2 m4 m8 | m1 m2 m4 m8 | BFAIL BFAIL BFAIL BFAIL |
| s351 | m1 **m1!** **m1!** **m1!** | m1 **m1!** **m1!** **m1!** | BFAIL BFAIL BFAIL BFAIL |
| s4112 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s4117 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s421 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s442 | m1 m2 m4 m8 | m1 m2 m4 m8 | BFAIL BFAIL BFAIL BFAIL |
| s443 | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |
| s452 | m1 m2 m4 **m4!** | m1 m2 m4 **m4!** | m1 m2 m4 m8 |
| vag | m1 m2 m4 **m4!** | m1 m2 m4 **m4!** | m1 m2 m4 m8 |
| vas | m1 m2 m4 **m4!** | m1 m2 m4 **m4!** | m1 m2 m4 m8 |
| vif | m1 m2 m4 m8 | m1 m2 m4 m8 | m1 m2 m4 m8 |

## 3. LMUL Mismatch Analysis

Only 13 true mismatches remain after correcting the detection logic (down from 39).

### 3.1 Always m1 — Compiler ignores LMUL hint entirely (1 kernel)

| Kernel | Pattern | Key Instructions | Affected Targets |
|--------|---------|-----------------|-----------------|
| s351 | Single-element FMA | vfmacc.vf | Saturn, XiangShan |

**Root cause**: s351 uses `vfmacc.vf` with a single scalar accumulation pattern. The compiler determines that higher LMUL provides no benefit since only one element is active.

> **Correction (2026-02-12)**: s252 and s254 were previously listed here as "Always m1"
> due to a detection bug. Both kernels use `vslidedown`/`vslideup` but **do correctly
> scale LMUL** — the loop body uses the requested m2/m4/m8. The false detection was
> caused by a prologue `vsetvli e32, m1` (for `vmv.s.x` scalar init) being matched
> before the loop body's higher LMUL.

### 3.2 LMUL=8 capped at m4 (3 kernels, rv64 only)

| Kernel | Constraint | Blocking Instruction | Saturn/XiangShan | T1 |
|--------|-----------|---------------------|-----------------|-----|
| vag | Widening multiply | `vwmulsu.vx` (m4→m8) | **m4!** | m8 |
| vas | Widening multiply | `vwmulsu.vx` (m4→m8) | **m4!** | m8 |
| s452 | Narrowing shift | `vnsrl.wi` | **m4!** | m8 |

**Root cause**: Widening operations (`vwmulsu.vx`) produce a result that is 2x the input width. At LMUL=4, the widened result occupies LMUL=8 worth of registers — the maximum. Therefore LMUL=8 input is impossible since the widened output would require LMUL=16 (which doesn't exist).

**T1 difference**: T1 uses rv32gcv where the widening/narrowing path is handled differently by LLVM, allowing m8 generation.

> **Correction (2026-02-12)**: s4112, s4117, s276 were previously listed as "capped at m4".
> These kernels use mixed-SEW operations (`e32` for data + `e64` for index/address).
> The `e64,m2` vsetvli was falsely counted as the primary LMUL. With e32-only detection,
> all three correctly use the requested LMUL for their primary e32 data operations.
> Similarly, s442 lmul=8 was reported as `mf4` — the `mf4` comes from an auxiliary
> vsetvli, not the primary e32 operations which correctly use m8.

### 3.3 T1-only: s128 LMUL=8 → m4

Only on T1 (rv32gcv). The rv32 backend inserts additional `vrgather.vv`, `vrsub.vi`, `vsrl.vi` instructions for the interleaved access pattern, causing register pressure that caps LMUL at m4.

## 4. T1 Build Failures

4 kernels fail to build for T1 (rv32gcv), all LMUL values:

| Kernel | Description | Likely Cause |
|--------|------------|-------------|
| s331 | Search (find max index) | 64-bit integer operations (index type) |
| s332 | Search (first match) | `vcpop.m`/`vfirst.m` with 64-bit types |
| s351 | Dot product variant | `long` type incompatibility |
| s442 | Indirect addressing | 64-bit index computation |

These kernels compiled and ran on T1 in previous experiments (producing scalar code), but the `--asm` generation in the verification script encountered nix environment issues.

## 5. Vector Instructions by Kernel

| Kernel | Category | Key Vector Instructions |
|--------|----------|----------------------|
| s000 | Linear (a+=b) | vfadd.vv |
| s121 | Stride-1 add | vfadd.vv |
| s124 | Conditional assign | vfmadd.vv, vmerge.vvm, vmfgt.vf |
| s1279 | Compound conditional | vfmacc.vv, vmand.mm, vmflt.vf, vmflt.vv |
| s128 | Interleaved access | vadd.vi/vv/vx, vfadd.vv, vfsub.vv, vid.v |
| s1281 | Multi-array FMA | vfadd.vf/vv, vfmacc.vv, vfmul.vv |
| s131 | Global sum (stride-1) | vfadd.vv |
| s1421 | Multi-dim add | vfadd.vv |
| s251 | FMA chain | vfmadd.vv, vfmul.vv |
| s252 | Recurrence (slide) | vfadd.vv, vfmul.vv, vslidedown.vx, vslideup.vi |
| s253 | Conditional FMA | vfadd.vv, vfnmsub.vv, vmflt.vv |
| s254 | Prefix scan (slide) | vfadd.vv, vfmul.vf, vslidedown.vx, vslideup.vi |
| s271 | Conditional accumulate | vfmacc.vv, vmfgt.vf |
| s2710 | If-else accumulate | vfmacc.vv, vfmadd.vv, vmflt.vv, vmnot.m |
| s276 | Indexed FMA | vadd.vv/vx, vfmadd.vv, vid.v, vmerge.vxm |
| s278 | Multi-branch FMA | vfmacc.vv, vfmsac.vv, vfmsub.vv, vmerge.vvm |
| s279 | Nested conditional | vfmacc.vv, vfmadd.vv, vfmsac.vv, vmandn.mm |
| s311 | Reduction (sum) | vfadd.vv, vfredusum.vs |
| s313 | Reduction (dot product) | vfmacc.vv, vfredusum.vs |
| s331 | Search (max index) | vmax.vv, vredmax.vs, vid.v, vcpop.m |
| s332 | Search (first match) | vcpop.m, vfirst.m, vslidedown.vx |
| s351 | Dot product (single-elem) | vfmacc.vf |
| s4112 | Mixed-width FMA | vfmacc.vf, vwmulsu.vx |
| s4117 | Indexed FMA (masked) | vadd.vx, vand.vx, vfmadd.vv, vid.v |
| s421 | Multi-dim add | vfadd.vv |
| s442 | Indirect addressing | vadd.vv/vx, vfmadd.vv, vid.v, vmseq.vi |
| s443 | Conditional accumulate | vfmacc.vv, vmfle.vf |
| s452 | Indexed FMA (computed) | vadd.vi/vx, vfcvt.f.xu.v, vfmadd.vv, vid.v |
| vag | Array gather | vwmulsu.vx (address calc) |
| vas | Array scatter | vwmulsu.vx (address calc) |
| vif | Conditional branch | vmfgt.vf |

## 6. Key Findings

### 6.1 All builds that succeed are vectorized

Of the 356 successful builds, **100% use vector instructions**. No kernel fell back to scalar code. This confirms that the LLVM vectorizer consistently enables RVV code generation for all TSVC-derived kernels with `-O2`.

### 6.2 LMUL hint is mostly respected

The `-mllvm -riscv-v-register-bit-width-lmul=N` flag is a **hint**, but LLVM follows it in the vast majority of cases (96.5%). LLVM overrides it only when:
- Widening/narrowing operations would exceed m8 (vag, vas, s452 on rv64)
- Single-element patterns make higher LMUL meaningless (s351)
- Register pressure on rv32 backend (s128 on T1)

Notably, even kernels with `vslidedown`/`vslideup` (s252, s254) correctly scale LMUL.

### 6.3 Saturn and XiangShan generate identical assembly

Both targets use rv64gcv, so LLVM produces the **same assembly** for both. All 6 LMUL mismatches are identical between them. Performance differences in simulation come entirely from microarchitectural differences (VLEN, pipeline depth, etc.), not from code generation.

### 6.4 T1 (rv32) has a distinct compilation path

The rv32gcv backend generates different code in several cases:
- Widening operations that cap at m4 on rv64 succeed at m8 on rv32
- Some kernels fail to build entirely due to 64-bit type requirements
- Additional instructions (vrgather, vrsub) appear for some access patterns

## 7. Raw Data

| File | Description |
|------|-------------|
| `all_vectorization.csv` | Merged CSV (372 rows) |
| `saturn/results.csv` | Saturn per-kernel results |
| `xiangshan/results.csv` | XiangShan per-kernel results |
| `t1/results.csv` | T1 per-kernel results |
| `saturn/*.s` | Saturn assembly files (124 files) |
| `xiangshan/*.s` | XiangShan assembly files (124 files) |
| `t1/*.s` | T1 assembly files (108 files) |
