#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb6_src0[LEN_1D];
static int16_t wb6_src1[LEN_1D];
static int16_t wb6_src2[LEN_1D];
static int32_t wb6_seed[LEN_1D];
static int32_t wb6_accum[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb6_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&wb6_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&wb6_src1[offset], vl);
    vint32m2_t seed = __riscv_vwadd_vv_i32m2(x, y, vl);
    __riscv_vse32_v_i32m2(&wb6_seed[offset], seed, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb6_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&wb6_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&wb6_src1[offset], vl);
    vint32m4_t seed = __riscv_vwadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&wb6_seed[offset], seed, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb6_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb6_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb6_src1[offset], vl);
    vint32m8_t seed = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb6_seed[offset], seed, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb6_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&wb6_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&wb6_src1[offset], vl);
    vint16m1_t z = __riscv_vle16_v_i16m1(&wb6_src2[offset], vl);
    vint32m2_t seed = __riscv_vle32_v_i32m2(&wb6_seed[offset], vl);
    vint32m2_t t0 = __riscv_vwmul_vv_i32m2(x, y, vl);
    vint32m2_t t1 = __riscv_vwmul_vv_i32m2(y, z, vl);
    vint32m2_t t2 = __riscv_vwadd_vv_i32m2(x, z, vl);
    vint32m2_t t3 = __riscv_vwmul_vv_i32m2(z, z, vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(seed, t0, vl);
    out = __riscv_vadd_vv_i32m2(out, t1, vl);
    out = __riscv_vadd_vv_i32m2(out, t2, vl);
    out = __riscv_vadd_vv_i32m2(out, t3, vl);
    __riscv_vse32_v_i32m2(&wb6_accum[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb6_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&wb6_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&wb6_src1[offset], vl);
    vint16m2_t z = __riscv_vle16_v_i16m2(&wb6_src2[offset], vl);
    vint32m4_t seed = __riscv_vle32_v_i32m4(&wb6_seed[offset], vl);
    vint32m4_t t0 = __riscv_vwmul_vv_i32m4(x, y, vl);
    vint32m4_t t1 = __riscv_vwmul_vv_i32m4(y, z, vl);
    vint32m4_t t2 = __riscv_vwadd_vv_i32m4(x, z, vl);
    vint32m4_t t3 = __riscv_vwmul_vv_i32m4(z, z, vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(seed, t0, vl);
    out = __riscv_vadd_vv_i32m4(out, t1, vl);
    out = __riscv_vadd_vv_i32m4(out, t2, vl);
    out = __riscv_vadd_vv_i32m4(out, t3, vl);
    __riscv_vse32_v_i32m4(&wb6_accum[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb6_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb6_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb6_src1[offset], vl);
    vint16m4_t z = __riscv_vle16_v_i16m4(&wb6_src2[offset], vl);
    vint32m8_t seed = __riscv_vle32_v_i32m8(&wb6_seed[offset], vl);
    vint32m8_t t0 = __riscv_vwmul_vv_i32m8(x, y, vl);
    vint32m8_t t1 = __riscv_vwmul_vv_i32m8(y, z, vl);
    vint32m8_t t2 = __riscv_vwadd_vv_i32m8(x, z, vl);
    vint32m8_t t3 = __riscv_vwmul_vv_i32m8(z, z, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(seed, t0, vl);
    out = __riscv_vadd_vv_i32m8(out, t1, vl);
    out = __riscv_vadd_vv_i32m8(out, t2, vl);
    out = __riscv_vadd_vv_i32m8(out, t3, vl);
    __riscv_vse32_v_i32m8(&wb6_accum[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb6_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vint32m1_t seed = __riscv_vle32_v_i32m1(&wb6_seed[offset], vl);
    vint32m1_t accum = __riscv_vle32_v_i32m1(&wb6_accum[offset], vl);
    vint32m1_t out = __riscv_vadd_vv_i32m1(seed, accum, vl);
    __riscv_vse32_v_i32m1(&indx[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb6_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vint32m2_t seed = __riscv_vle32_v_i32m2(&wb6_seed[offset], vl);
    vint32m2_t accum = __riscv_vle32_v_i32m2(&wb6_accum[offset], vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(seed, accum, vl);
    __riscv_vse32_v_i32m2(&indx[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb6_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t seed = __riscv_vle32_v_i32m4(&wb6_seed[offset], vl);
    vint32m4_t accum = __riscv_vle32_v_i32m4(&wb6_accum[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(seed, accum, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb6_src0, wb6_src1, wb6_src2, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb6_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb6_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb6_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
