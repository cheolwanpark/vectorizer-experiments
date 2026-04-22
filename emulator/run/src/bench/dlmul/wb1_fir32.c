#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vin = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t vt0 = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t vt1 = __riscv_vle32_v_f32m1(&x[offset], vl);
    vfloat32m1_t mix = __riscv_vfadd_vv_f32m1(vt0, vt1, vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(vin, mix, vl);
    __riscv_vse32_v_f32m1(&d[offset], out, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t vin = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t vt0 = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t vt1 = __riscv_vle32_v_f32m2(&x[offset], vl);
    vfloat32m2_t mix = __riscv_vfadd_vv_f32m2(vt0, vt1, vl);
    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(vin, mix, vl);
    __riscv_vse32_v_f32m2(&d[offset], out, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vin = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t vt0 = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t vt1 = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t mix = __riscv_vfadd_vv_f32m4(vt0, vt1, vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(vin, mix, vl);
    __riscv_vse32_v_f32m4(&d[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t v0 = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t v1 = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t v2 = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t v3 = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t acc = __riscv_vfmul_vv_f32m1(v0, v1, vl);
    acc = __riscv_vfmacc_vv_f32m1(acc, v2, v3, vl);
    acc = __riscv_vfadd_vv_f32m1(acc, v0, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[offset], acc, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t v0 = __riscv_vle32_v_f32m2(&d[offset], vl);
    vfloat32m2_t v1 = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t v2 = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t v3 = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t acc = __riscv_vfmul_vv_f32m2(v0, v1, vl);
    acc = __riscv_vfmacc_vv_f32m2(acc, v2, v3, vl);
    acc = __riscv_vfadd_vv_f32m2(acc, v0, vl);
    __riscv_vse32_v_f32m2(&flat_2d_array[offset], acc, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t v0 = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t v1 = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t v2 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t v3 = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t acc = __riscv_vfmul_vv_f32m4(v0, v1, vl);
    acc = __riscv_vfmacc_vv_f32m4(acc, v2, v3, vl);
    acc = __riscv_vfadd_vv_f32m4(acc, v0, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], acc, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t acc = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t base = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(base, 0.125f, acc, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t acc = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t base = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(base, 0.125f, acc, vl);
    __riscv_vse32_v_f32m2(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t acc = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t base = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(base, 0.125f, acc, vl);
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
            size_t vl = wb1_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb1_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb1_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
