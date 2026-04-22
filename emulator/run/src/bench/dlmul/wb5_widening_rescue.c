#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];
static int32_t wb5_phase1[LEN_1D];
static int32_t wb5_phase2[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&wb5_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&wb5_src1[offset], vl);
    vint32m2_t partial = __riscv_vwadd_vv_i32m2(x, y, vl);
    __riscv_vse32_v_i32m2(&wb5_phase1[offset], partial, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&wb5_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&wb5_src1[offset], vl);
    vint32m4_t partial = __riscv_vwadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&wb5_phase1[offset], partial, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
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
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&wb5_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&wb5_src1[offset], vl);
    vint16m2_t z = __riscv_vle16_v_i16m2(&wb5_src2[offset], vl);
    vint32m4_t seed = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t t0 = __riscv_vwadd_vv_i32m4(x, y, vl);
    vint32m4_t t1 = __riscv_vwmul_vv_i32m4(x, y, vl);
    vint32m4_t t2 = __riscv_vwadd_vv_i32m4(y, z, vl);
    vint32m4_t t3 = __riscv_vwmul_vv_i32m4(y, z, vl);
    vint32m4_t t4 = __riscv_vwadd_vv_i32m4(x, z, vl);
    vint32m4_t t5 = __riscv_vwmul_vv_i32m4(x, z, vl);
    vint32m4_t t6 = __riscv_vwadd_vv_i32m4(x, x, vl);
    vint32m4_t t7 = __riscv_vwadd_vv_i32m4(y, y, vl);
    vint32m4_t t8 = __riscv_vwmul_vv_i32m4(z, z, vl);
    vint32m4_t t9 = __riscv_vwmul_vv_i32m4(y, x, vl);
    vint32m4_t t10 = __riscv_vwadd_vv_i32m4(z, x, vl);
    vint32m4_t t11 = __riscv_vwmul_vv_i32m4(z, y, vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(seed, t0, vl);
    out = __riscv_vadd_vv_i32m4(out, t1, vl);
    out = __riscv_vadd_vv_i32m4(out, t2, vl);
    out = __riscv_vadd_vv_i32m4(out, t3, vl);
    out = __riscv_vadd_vv_i32m4(out, t4, vl);
    out = __riscv_vadd_vv_i32m4(out, t5, vl);
    out = __riscv_vadd_vv_i32m4(out, t6, vl);
    out = __riscv_vadd_vv_i32m4(out, t7, vl);
    out = __riscv_vadd_vv_i32m4(out, t8, vl);
    out = __riscv_vadd_vv_i32m4(out, t9, vl);
    out = __riscv_vadd_vv_i32m4(out, t10, vl);
    out = __riscv_vadd_vv_i32m4(out, t11, vl);
    __riscv_vse32_v_i32m4(&wb5_phase2[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
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
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vint32m1_t x = __riscv_vle32_v_i32m1(&wb5_phase1[offset], vl);
    vint32m1_t y = __riscv_vle32_v_i32m1(&wb5_phase2[offset], vl);
    vint32m1_t out = __riscv_vadd_vv_i32m1(x, y, vl);
    __riscv_vse32_v_i32m1(&indx[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vint32m2_t x = __riscv_vle32_v_i32m2(&wb5_phase1[offset], vl);
    vint32m2_t y = __riscv_vle32_v_i32m2(&wb5_phase2[offset], vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(x, y, vl);
    __riscv_vse32_v_i32m2(&indx[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
