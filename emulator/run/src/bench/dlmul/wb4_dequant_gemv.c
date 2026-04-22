#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb4_activation[LEN_1D];
static int16_t wb4_weight[LEN_1D];
static int16_t wb4_bias16[LEN_1D];
static int32_t wb4_partial[LEN_1D];
static int32_t wb4_output[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb4_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t act = __riscv_vle16_v_i16m1(&wb4_activation[offset], vl);
    vint16m1_t wt = __riscv_vle16_v_i16m1(&wb4_weight[offset], vl);
    vint32m2_t widened = __riscv_vwadd_vv_i32m2(act, wt, vl);
    __riscv_vse32_v_i32m2(&wb4_partial[offset], widened, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb4_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t act = __riscv_vle16_v_i16m2(&wb4_activation[offset], vl);
    vint16m2_t wt = __riscv_vle16_v_i16m2(&wb4_weight[offset], vl);
    vint32m4_t widened = __riscv_vwadd_vv_i32m4(act, wt, vl);
    __riscv_vse32_v_i32m4(&wb4_partial[offset], widened, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb4_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act = __riscv_vle16_v_i16m4(&wb4_activation[offset], vl);
    vint16m4_t wt = __riscv_vle16_v_i16m4(&wb4_weight[offset], vl);
    vint32m8_t widened = __riscv_vwadd_vv_i32m8(act, wt, vl);
    __riscv_vse32_v_i32m8(&wb4_partial[offset], widened, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb4_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t act = __riscv_vle16_v_i16m1(&wb4_activation[offset], vl);
    vint16m1_t wt = __riscv_vle16_v_i16m1(&wb4_weight[offset], vl);
    vint16m1_t bias = __riscv_vle16_v_i16m1(&wb4_bias16[offset], vl);
    vint32m2_t partial = __riscv_vle32_v_i32m2(&wb4_partial[offset], vl);
    vint32m2_t acc0 = __riscv_vwmul_vv_i32m2(act, wt, vl);
    vint32m2_t acc1 = __riscv_vwmul_vv_i32m2(act, bias, vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(partial, acc0, vl);
    out = __riscv_vadd_vv_i32m2(out, acc1, vl);
    __riscv_vse32_v_i32m2(&wb4_output[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb4_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t act = __riscv_vle16_v_i16m2(&wb4_activation[offset], vl);
    vint16m2_t wt = __riscv_vle16_v_i16m2(&wb4_weight[offset], vl);
    vint16m2_t bias = __riscv_vle16_v_i16m2(&wb4_bias16[offset], vl);
    vint32m4_t partial = __riscv_vle32_v_i32m4(&wb4_partial[offset], vl);
    vint32m4_t acc0 = __riscv_vwmul_vv_i32m4(act, wt, vl);
    vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(act, bias, vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(partial, acc0, vl);
    out = __riscv_vadd_vv_i32m4(out, acc1, vl);
    __riscv_vse32_v_i32m4(&wb4_output[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb4_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act = __riscv_vle16_v_i16m4(&wb4_activation[offset], vl);
    vint16m4_t wt = __riscv_vle16_v_i16m4(&wb4_weight[offset], vl);
    vint16m4_t bias = __riscv_vle16_v_i16m4(&wb4_bias16[offset], vl);
    vint32m8_t partial = __riscv_vle32_v_i32m8(&wb4_partial[offset], vl);
    vint32m8_t acc0 = __riscv_vwmul_vv_i32m8(act, wt, vl);
    vint32m8_t acc1 = __riscv_vwmul_vv_i32m8(act, bias, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(partial, acc0, vl);
    out = __riscv_vadd_vv_i32m8(out, acc1, vl);
    __riscv_vse32_v_i32m8(&wb4_output[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb4_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vint32m1_t out = __riscv_vle32_v_i32m1(&wb4_output[offset], vl);
    vint32m1_t partial = __riscv_vle32_v_i32m1(&wb4_partial[offset], vl);
    vint32m1_t fused = __riscv_vadd_vv_i32m1(out, partial, vl);
    __riscv_vse32_v_i32m1(&indx[offset], fused, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb4_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vint32m2_t out = __riscv_vle32_v_i32m2(&wb4_output[offset], vl);
    vint32m2_t partial = __riscv_vle32_v_i32m2(&wb4_partial[offset], vl);
    vint32m2_t fused = __riscv_vadd_vv_i32m2(out, partial, vl);
    __riscv_vse32_v_i32m2(&indx[offset], fused, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb4_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t out = __riscv_vle32_v_i32m4(&wb4_output[offset], vl);
    vint32m4_t partial = __riscv_vle32_v_i32m4(&wb4_partial[offset], vl);
    vint32m4_t fused = __riscv_vadd_vv_i32m4(out, partial, vl);
    __riscv_vse32_v_i32m4(&indx[offset], fused, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb4_activation, wb4_weight, wb4_bias16, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb4_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb4_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb4_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
