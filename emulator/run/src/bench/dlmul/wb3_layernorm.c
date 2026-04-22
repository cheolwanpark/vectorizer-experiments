#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb3_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vin = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t vshift = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t sum = __riscv_vfadd_vv_f32m1(vin, vshift, vl);
    vfloat32m1_t sq = __riscv_vfmul_vv_f32m1(vin, vin, vl);
    __riscv_vse32_v_f32m1(&d[offset], sum, vl);
    __riscv_vse32_v_f32m1(&e[offset], sq, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb3_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t vin = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t vshift = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t sum = __riscv_vfadd_vv_f32m2(vin, vshift, vl);
    vfloat32m2_t sq = __riscv_vfmul_vv_f32m2(vin, vin, vl);
    __riscv_vse32_v_f32m2(&d[offset], sum, vl);
    __riscv_vse32_v_f32m2(&e[offset], sq, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb3_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vin = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t vshift = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t sum = __riscv_vfadd_vv_f32m4(vin, vshift, vl);
    vfloat32m4_t sq = __riscv_vfmul_vv_f32m4(vin, vin, vl);
    __riscv_vse32_v_f32m4(&d[offset], sum, vl);
    __riscv_vse32_v_f32m4(&e[offset], sq, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb3_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t sum = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t sq = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t scale = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t bias = __riscv_vle32_v_f32m1(&x[offset], vl);
    vfloat32m1_t rsqrt_like = __riscv_vfadd_vf_f32m1(sq, 1.0f, vl);
    vfloat32m1_t centered = __riscv_vfsub_vv_f32m1(sum, bias, vl);
    vfloat32m1_t out = __riscv_vfmul_vv_f32m1(centered, scale, vl);
    out = __riscv_vfdiv_vv_f32m1(out, rsqrt_like, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb3_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t sum = __riscv_vle32_v_f32m2(&d[offset], vl);
    vfloat32m2_t sq = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t scale = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t bias = __riscv_vle32_v_f32m2(&x[offset], vl);
    vfloat32m2_t rsqrt_like = __riscv_vfadd_vf_f32m2(sq, 1.0f, vl);
    vfloat32m2_t centered = __riscv_vfsub_vv_f32m2(sum, bias, vl);
    vfloat32m2_t out = __riscv_vfmul_vv_f32m2(centered, scale, vl);
    out = __riscv_vfdiv_vv_f32m2(out, rsqrt_like, vl);
    __riscv_vse32_v_f32m2(&flat_2d_array[offset], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb3_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t sum = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t sq = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t scale = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t bias = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t rsqrt_like = __riscv_vfadd_vf_f32m4(sq, 1.0f, vl);
    vfloat32m4_t centered = __riscv_vfsub_vv_f32m4(sum, bias, vl);
    vfloat32m4_t out = __riscv_vfmul_vv_f32m4(centered, scale, vl);
    out = __riscv_vfdiv_vv_f32m4(out, rsqrt_like, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb3_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t normed = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t affine = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(affine, 0.5f, normed, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb3_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t normed = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t affine = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(affine, 0.5f, normed, vl);
    __riscv_vse32_v_f32m2(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb3_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t normed = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(affine, 0.5f, normed, vl);
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
            size_t vl = wb3_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb3_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb3_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
