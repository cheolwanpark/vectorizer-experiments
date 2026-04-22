#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t x0 = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t x1 = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t seed = __riscv_vfadd_vv_f32m1(x0, x1, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[offset], seed, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t x0 = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t x1 = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t seed = __riscv_vfadd_vv_f32m2(x0, x1, vl);
    __riscv_vse32_v_f32m2(&flat_2d_array[offset], seed, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t x0 = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t seed = __riscv_vfadd_vv_f32m4(x0, x1, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], seed, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t seed = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t x0 = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t x1 = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t x2 = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t x3 = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t x4 = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t x5 = __riscv_vle32_v_f32m1(&x[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(seed, x0, vl);
    out = __riscv_vfadd_vv_f32m1(out, x1, vl);
    out = __riscv_vfadd_vv_f32m1(out, x2, vl);
    out = __riscv_vfadd_vv_f32m1(out, x3, vl);
    out = __riscv_vfadd_vv_f32m1(out, x4, vl);
    out = __riscv_vfadd_vv_f32m1(out, x5, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t seed = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t x0 = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t x1 = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t x2 = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t x3 = __riscv_vle32_v_f32m2(&d[offset], vl);
    vfloat32m2_t x4 = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t x5 = __riscv_vle32_v_f32m2(&x[offset], vl);
    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(seed, x0, vl);
    out = __riscv_vfadd_vv_f32m2(out, x1, vl);
    out = __riscv_vfadd_vv_f32m2(out, x2, vl);
    out = __riscv_vfadd_vv_f32m2(out, x3, vl);
    out = __riscv_vfadd_vv_f32m2(out, x4, vl);
    out = __riscv_vfadd_vv_f32m2(out, x5, vl);
    __riscv_vse32_v_f32m2(&flat_2d_array[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t seed = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t x0 = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t x2 = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t x3 = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t x4 = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t x5 = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(seed, x0, vl);
    out = __riscv_vfadd_vv_f32m4(out, x1, vl);
    out = __riscv_vfadd_vv_f32m4(out, x2, vl);
    out = __riscv_vfadd_vv_f32m4(out, x3, vl);
    out = __riscv_vfadd_vv_f32m4(out, x4, vl);
    out = __riscv_vfadd_vv_f32m4(out, x5, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t fused = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t affine = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(fused, affine, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t fused = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t affine = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(fused, affine, vl);
    __riscv_vse32_v_f32m2(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(fused, affine, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb9_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb9_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb9_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
