#include "common.h"
#include "dlmul_variant.h"
#include <stdint.h>
#include <riscv_vector.h>

#ifndef MB5_LMUL_VARIANT
#define MB5_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB5_ACC_COUNT
#define MB5_ACC_COUNT 2
#endif

#ifndef MB5_TOTAL_ELEMS
#define MB5_TOTAL_ELEMS 64
#endif

#ifndef MB5_OUTER_ITERS
#define MB5_OUTER_ITERS 32
#endif

static int16_t mb5_src0[LEN_1D];
static int16_t mb5_src1[LEN_1D];
static int32_t mb5_dst[LEN_1D];

#if MB5_LMUL_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb5_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16mf2(avl);
    vint16mf2_t x = __riscv_vle16_v_i16mf2(&mb5_src0[offset], vl);
    vint16mf2_t y = __riscv_vle16_v_i16mf2(&mb5_src1[offset], vl);
    vint32m1_t acc0 = __riscv_vwadd_vv_i32m1(x, y, vl);
    vint32m1_t acc1 = __riscv_vwmul_vv_i32m1(x, y, vl);
#if MB5_ACC_COUNT >= 4
    vint32m1_t acc2 = __riscv_vwadd_vv_i32m1(y, x, vl);
    vint32m1_t acc3 = __riscv_vwmul_vv_i32m1(y, x, vl);
#endif
#if MB5_ACC_COUNT >= 8
    vint32m1_t acc4 = __riscv_vwadd_vv_i32m1(x, x, vl);
    vint32m1_t acc5 = __riscv_vwadd_vv_i32m1(y, y, vl);
    vint32m1_t acc6 = __riscv_vwmul_vv_i32m1(x, x, vl);
    vint32m1_t acc7 = __riscv_vwmul_vv_i32m1(y, y, vl);
#endif
    vint32m1_t out = __riscv_vadd_vv_i32m1(acc0, acc1, vl);
#if MB5_ACC_COUNT >= 4
    out = __riscv_vadd_vv_i32m1(out, acc2, vl);
    out = __riscv_vadd_vv_i32m1(out, acc3, vl);
#endif
#if MB5_ACC_COUNT >= 8
    out = __riscv_vadd_vv_i32m1(out, acc4, vl);
    out = __riscv_vadd_vv_i32m1(out, acc5, vl);
    out = __riscv_vadd_vv_i32m1(out, acc6, vl);
    out = __riscv_vadd_vv_i32m1(out, acc7, vl);
#endif
    __riscv_vse32_v_i32m1(&mb5_dst[offset], out, vl);
    return vl;
}
#elif MB5_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb5_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&mb5_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&mb5_src1[offset], vl);
    vint32m2_t acc0 = __riscv_vwadd_vv_i32m2(x, y, vl);
    vint32m2_t acc1 = __riscv_vwmul_vv_i32m2(x, y, vl);
#if MB5_ACC_COUNT >= 4
    vint32m2_t acc2 = __riscv_vwadd_vv_i32m2(y, x, vl);
    vint32m2_t acc3 = __riscv_vwmul_vv_i32m2(y, x, vl);
#endif
#if MB5_ACC_COUNT >= 8
    vint32m2_t acc4 = __riscv_vwadd_vv_i32m2(x, x, vl);
    vint32m2_t acc5 = __riscv_vwadd_vv_i32m2(y, y, vl);
    vint32m2_t acc6 = __riscv_vwmul_vv_i32m2(x, x, vl);
    vint32m2_t acc7 = __riscv_vwmul_vv_i32m2(y, y, vl);
#endif
    vint32m2_t out = __riscv_vadd_vv_i32m2(acc0, acc1, vl);
#if MB5_ACC_COUNT >= 4
    out = __riscv_vadd_vv_i32m2(out, acc2, vl);
    out = __riscv_vadd_vv_i32m2(out, acc3, vl);
#endif
#if MB5_ACC_COUNT >= 8
    out = __riscv_vadd_vv_i32m2(out, acc4, vl);
    out = __riscv_vadd_vv_i32m2(out, acc5, vl);
    out = __riscv_vadd_vv_i32m2(out, acc6, vl);
    out = __riscv_vadd_vv_i32m2(out, acc7, vl);
#endif
    __riscv_vse32_v_i32m2(&mb5_dst[offset], out, vl);
    return vl;
}
#elif MB5_LMUL_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb5_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&mb5_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&mb5_src1[offset], vl);
    vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x, y, vl);
    vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x, y, vl);
#if MB5_ACC_COUNT >= 4
    vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(y, x, vl);
    vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(y, x, vl);
#endif
#if MB5_ACC_COUNT >= 8
    vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x, x, vl);
    vint32m4_t acc5 = __riscv_vwadd_vv_i32m4(y, y, vl);
    vint32m4_t acc6 = __riscv_vwmul_vv_i32m4(x, x, vl);
    vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(y, y, vl);
#endif
    vint32m4_t out = __riscv_vadd_vv_i32m4(acc0, acc1, vl);
#if MB5_ACC_COUNT >= 4
    out = __riscv_vadd_vv_i32m4(out, acc2, vl);
    out = __riscv_vadd_vv_i32m4(out, acc3, vl);
#endif
#if MB5_ACC_COUNT >= 8
    out = __riscv_vadd_vv_i32m4(out, acc4, vl);
    out = __riscv_vadd_vv_i32m4(out, acc5, vl);
    out = __riscv_vadd_vv_i32m4(out, acc6, vl);
    out = __riscv_vadd_vv_i32m4(out, acc7, vl);
#endif
    __riscv_vse32_v_i32m4(&mb5_dst[offset], out, vl);
    return vl;
}
#elif MB5_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb5_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&mb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&mb5_src1[offset], vl);
    vint32m8_t acc0 = __riscv_vwadd_vv_i32m8(x, y, vl);
    vint32m8_t acc1 = __riscv_vwmul_vv_i32m8(x, y, vl);
#if MB5_ACC_COUNT >= 4
    vint32m8_t acc2 = __riscv_vwadd_vv_i32m8(y, x, vl);
    vint32m8_t acc3 = __riscv_vwmul_vv_i32m8(y, x, vl);
#endif
#if MB5_ACC_COUNT >= 8
    vint32m8_t acc4 = __riscv_vwadd_vv_i32m8(x, x, vl);
    vint32m8_t acc5 = __riscv_vwadd_vv_i32m8(y, y, vl);
    vint32m8_t acc6 = __riscv_vwmul_vv_i32m8(x, x, vl);
    vint32m8_t acc7 = __riscv_vwmul_vv_i32m8(y, y, vl);
#endif
    vint32m8_t out = __riscv_vadd_vv_i32m8(acc0, acc1, vl);
#if MB5_ACC_COUNT >= 4
    out = __riscv_vadd_vv_i32m8(out, acc2, vl);
    out = __riscv_vadd_vv_i32m8(out, acc3, vl);
#endif
#if MB5_ACC_COUNT >= 8
    out = __riscv_vadd_vv_i32m8(out, acc4, vl);
    out = __riscv_vadd_vv_i32m8(out, acc5, vl);
    out = __riscv_vadd_vv_i32m8(out, acc6, vl);
    out = __riscv_vadd_vv_i32m8(out, acc7, vl);
#endif
    __riscv_vse32_v_i32m8(&mb5_dst[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB5_LMUL_VARIANT"
#endif

void kernel(void) {
    for (int i = 0; i < MB5_TOTAL_ELEMS; ++i) {
        mb5_src0[i] = (int16_t)((i % 17) + 1);
        mb5_src1[i] = (int16_t)((i % 13) + 2);
    }
    for (int iter = 0; iter < MB5_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB5_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb5_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
