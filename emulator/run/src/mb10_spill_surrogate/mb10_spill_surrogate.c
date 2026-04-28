#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB10_LMUL_VARIANT
#define MB10_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB10_TRAFFIC_LEVEL
#define MB10_TRAFFIC_LEVEL 1
#endif

#ifndef MB10_TOTAL_ELEMS
#define MB10_TOTAL_ELEMS 128
#endif

#ifndef MB10_OUTER_ITERS
#define MB10_OUTER_ITERS 24
#endif

#define MB10_EXTRA_PASSES (MB10_TRAFFIC_LEVEL * 2)

#if MB10_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb10_compute_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t out = __riscv_vfmacc_vv_f32m1(va, vb, vb, vl);
    __riscv_vse32_v_f32m1(&d[offset], out, vl);
    return vl;
}

static __attribute__((noinline)) size_t mb10_spill_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], vl);
    __riscv_vse32_v_f32m1(&e[offset], vd, vl);
    return vl;
}
#elif MB10_LMUL_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb10_compute_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t out = __riscv_vfmacc_vv_f32m2(va, vb, vb, vl);
    __riscv_vse32_v_f32m2(&d[offset], out, vl);
    return vl;
}

static __attribute__((noinline)) size_t mb10_spill_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], vl);
    __riscv_vse32_v_f32m2(&e[offset], vd, vl);
    return vl;
}
#elif MB10_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb10_compute_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfmacc_vv_f32m4(va, vb, vb, vl);
    __riscv_vse32_v_f32m4(&d[offset], out, vl);
    return vl;
}

static __attribute__((noinline)) size_t mb10_spill_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], vl);
    __riscv_vse32_v_f32m4(&e[offset], vd, vl);
    return vl;
}
#else
#error "unsupported MB10_LMUL_VARIANT"
#endif

void kernel(void) {
    for (int iter = 0; iter < MB10_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB10_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb10_compute_step(offset, (size_t)remaining);
            for (int p = 0; p < MB10_EXTRA_PASSES; ++p) {
                (void)mb10_spill_step(offset, vl);
            }
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
