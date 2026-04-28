# `wb5` Compare

DB: `artifacts/dlmul-bench.sqlite`  
Case in DB: `wb5-widening-rescue`

| Variant | Phase LMUL (`p1/p2/p3`) | Total elems (`p1/p2/p3`) | Outer iters | Kernel cycles | Total cycles |
| --- | --- | --- | ---: | ---: | ---: |
| `dyn_safe` | `m4 / m1 / m4` | `64 / 128 / 64` | 24 | 20,882 | 59,712 |
| `fixed_m4` | `m4 / m4 / m4` | `64 / 128 / 64` | 24 | 24,329 | 66,511 |

`dyn_safe` is faster than `fixed_m4` by:

- kernel cycles: `3,447` (`14.17%`)
- total cycles: `6,799` (`10.22%`)

## `fixed_m4` Pseudo Code

```text
kernel():
  init wb5_src0, wb5_src1, wb5_src2

  repeat 24 times:
    phase1 over 64 elems with LMUL=m4
      load src0/src1 as e16,m4
      widen add -> i32,m8
      store wb5_phase1

    phase2 over 128 elems with LMUL=m4
      load src0/src1/src2 as e16,m4
      load wb5_phase1 seed as i32,m8
      build 12 widening temporaries at m8
      accumulate all temporaries into one m8 result
      store wb5_phase2

    phase3 over 64 elems with LMUL=m4
      load wb5_phase1/wb5_phase2 as e32,m4
      add
      store indx
```

## `fixed_m4` Complete Source

```c
#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];
static int32_t wb5_phase1[LEN_1D];
static int32_t wb5_phase2[LEN_1D];

static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial, vl);
    return vl;
}

static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint16m4_t z = __riscv_vle16_v_i16m4(&wb5_src2[offset], vl);
    vint32m8_t seed = __riscv_vle32_v_i32m8(&wb5_phase1[offset], vl);
    vint32m8_t t0 = __riscv_vwadd_vv_i32m8(x, y, vl);
    vint32m8_t t1 = __riscv_vwmul_vv_i32m8(x, y, vl);
    vint32m8_t t2 = __riscv_vwadd_vv_i32m8(y, z, vl);
    vint32m8_t t3 = __riscv_vwmul_vv_i32m8(y, z, vl);
    vint32m8_t t4 = __riscv_vwadd_vv_i32m8(x, z, vl);
    vint32m8_t t5 = __riscv_vwmul_vv_i32m8(x, z, vl);
    vint32m8_t t6 = __riscv_vwadd_vv_i32m8(x, x, vl);
    vint32m8_t t7 = __riscv_vwadd_vv_i32m8(y, y, vl);
    vint32m8_t t8 = __riscv_vwmul_vv_i32m8(z, z, vl);
    vint32m8_t t9 = __riscv_vwmul_vv_i32m8(y, x, vl);
    vint32m8_t t10 = __riscv_vwadd_vv_i32m8(z, x, vl);
    vint32m8_t t11 = __riscv_vwmul_vv_i32m8(z, y, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(seed, t0, vl);
    out = __riscv_vadd_vv_i32m8(out, t1, vl);
    out = __riscv_vadd_vv_i32m8(out, t2, vl);
    out = __riscv_vadd_vv_i32m8(out, t3, vl);
    out = __riscv_vadd_vv_i32m8(out, t4, vl);
    out = __riscv_vadd_vv_i32m8(out, t5, vl);
    out = __riscv_vadd_vv_i32m8(out, t6, vl);
    out = __riscv_vadd_vv_i32m8(out, t7, vl);
    out = __riscv_vadd_vv_i32m8(out, t8, vl);
    out = __riscv_vadd_vv_i32m8(out, t9, vl);
    out = __riscv_vadd_vv_i32m8(out, t10, vl);
    out = __riscv_vadd_vv_i32m8(out, t11, vl);
    __riscv_vse32_v_i32m8(&wb5_phase2[offset], out, vl);
    return vl;
}

static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}

void kernel(void) {
    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        int offset = 0;
        int remaining = 64;
        while (remaining > 0) {
            size_t vl = wb5_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = 128;
        while (remaining > 0) {
            size_t vl = wb5_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = 64;
        while (remaining > 0) {
            size_t vl = wb5_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
```

## `dyn_safe` Pseudo Code

```text
kernel():
  init wb5_src0, wb5_src1, wb5_src2

  repeat 24 times:
    phase1 over 64 elems with LMUL=m4
      load src0/src1 as e16,m4
      widen add -> i32,m8
      store wb5_phase1

    phase2 over 128 elems with LMUL=m1
      load src0/src1/src2 as e16,m1
      load wb5_phase1 seed as i32,m2
      build the same 12 widening temporaries, but at m2
      accumulate all temporaries into one m2 result
      store wb5_phase2
      repeat more smaller chunks because phase2 uses m1 instead of m4

    phase3 over 64 elems with LMUL=m4
      load wb5_phase1/wb5_phase2 as e32,m4
      add
      store indx
```

## `dyn_safe` Complete Source

```c
#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];
static int32_t wb5_phase1[LEN_1D];
static int32_t wb5_phase2[LEN_1D];

static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial, vl);
    return vl;
}

static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&wb5_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&wb5_src1[offset], vl);
    vint16m1_t z = __riscv_vle16_v_i16m1(&wb5_src2[offset], vl);
    vint32m2_t seed = __riscv_vle32_v_i32m2(&wb5_phase1[offset], vl);
    vint32m2_t t0 = __riscv_vwadd_vv_i32m2(x, y, vl);
    vint32m2_t t1 = __riscv_vwmul_vv_i32m2(x, y, vl);
    vint32m2_t t2 = __riscv_vwadd_vv_i32m2(y, z, vl);
    vint32m2_t t3 = __riscv_vwmul_vv_i32m2(y, z, vl);
    vint32m2_t t4 = __riscv_vwadd_vv_i32m2(x, z, vl);
    vint32m2_t t5 = __riscv_vwmul_vv_i32m2(x, z, vl);
    vint32m2_t t6 = __riscv_vwadd_vv_i32m2(x, x, vl);
    vint32m2_t t7 = __riscv_vwadd_vv_i32m2(y, y, vl);
    vint32m2_t t8 = __riscv_vwmul_vv_i32m2(z, z, vl);
    vint32m2_t t9 = __riscv_vwmul_vv_i32m2(y, x, vl);
    vint32m2_t t10 = __riscv_vwadd_vv_i32m2(z, x, vl);
    vint32m2_t t11 = __riscv_vwmul_vv_i32m2(z, y, vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(seed, t0, vl);
    out = __riscv_vadd_vv_i32m2(out, t1, vl);
    out = __riscv_vadd_vv_i32m2(out, t2, vl);
    out = __riscv_vadd_vv_i32m2(out, t3, vl);
    out = __riscv_vadd_vv_i32m2(out, t4, vl);
    out = __riscv_vadd_vv_i32m2(out, t5, vl);
    out = __riscv_vadd_vv_i32m2(out, t6, vl);
    out = __riscv_vadd_vv_i32m2(out, t7, vl);
    out = __riscv_vadd_vv_i32m2(out, t8, vl);
    out = __riscv_vadd_vv_i32m2(out, t9, vl);
    out = __riscv_vadd_vv_i32m2(out, t10, vl);
    out = __riscv_vadd_vv_i32m2(out, t11, vl);
    __riscv_vse32_v_i32m2(&wb5_phase2[offset], out, vl);
    return vl;
}

static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}

void kernel(void) {
    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        int offset = 0;
        int remaining = 64;
        while (remaining > 0) {
            size_t vl = wb5_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = 128;
        while (remaining > 0) {
            size_t vl = wb5_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = 64;
        while (remaining > 0) {
            size_t vl = wb5_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
```
