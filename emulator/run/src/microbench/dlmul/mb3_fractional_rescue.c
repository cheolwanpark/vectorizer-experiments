#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB3_VARIANT
#define MB3_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB3_TEMP_COUNT
#define MB3_TEMP_COUNT 8
#endif

#ifndef MB3_TOTAL_ELEMS
#define MB3_TOTAL_ELEMS 64
#endif

#ifndef MB3_OUTER_ITERS
#define MB3_OUTER_ITERS 48
#endif

#if MB3_VARIANT == DLMUL_LMUL_MF4
static __attribute__((noinline)) size_t mb3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf4(avl);
    vfloat32mf4_t v0 = __riscv_vle32_v_f32mf4(&a[offset], vl);
    vfloat32mf4_t v1 = __riscv_vle32_v_f32mf4(&b[offset], vl);
    vfloat32mf4_t v2 = __riscv_vle32_v_f32mf4(&c[offset], vl);
    vfloat32mf4_t v3 = __riscv_vle32_v_f32mf4(&d[offset], vl);
    vfloat32mf4_t v4 = __riscv_vle32_v_f32mf4(&e[offset], vl);
    vfloat32mf4_t v5 = __riscv_vle32_v_f32mf4(&x[offset], vl);
    vfloat32mf4_t v6 = __riscv_vle32_v_f32mf4(&aa[0][offset], vl);
    vfloat32mf4_t v7 = __riscv_vle32_v_f32mf4(&flat_2d_array[offset], vl);
    vfloat32mf4_t acc = __riscv_vfadd_vv_f32mf4(v0, v1, vl);
    acc = __riscv_vfadd_vv_f32mf4(acc, __riscv_vfmul_vv_f32mf4(v2, v3, vl), vl);
    acc = __riscv_vfadd_vv_f32mf4(acc, __riscv_vfmul_vv_f32mf4(v4, v5, vl), vl);
    acc = __riscv_vfsub_vv_f32mf4(acc, v6, vl);
    acc = __riscv_vfadd_vv_f32mf4(acc, v7, vl);
    __riscv_vse32_v_f32mf4(&d[offset], acc, vl);
    return vl;
}
#elif MB3_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf2(avl);
    vfloat32mf2_t v0 = __riscv_vle32_v_f32mf2(&a[offset], vl);
    vfloat32mf2_t v1 = __riscv_vle32_v_f32mf2(&b[offset], vl);
    vfloat32mf2_t v2 = __riscv_vle32_v_f32mf2(&c[offset], vl);
    vfloat32mf2_t v3 = __riscv_vle32_v_f32mf2(&d[offset], vl);
    vfloat32mf2_t v4 = __riscv_vle32_v_f32mf2(&e[offset], vl);
    vfloat32mf2_t v5 = __riscv_vle32_v_f32mf2(&x[offset], vl);
    vfloat32mf2_t v6 = __riscv_vle32_v_f32mf2(&aa[0][offset], vl);
    vfloat32mf2_t v7 = __riscv_vle32_v_f32mf2(&flat_2d_array[offset], vl);
    vfloat32mf2_t acc = __riscv_vfadd_vv_f32mf2(v0, v1, vl);
    acc = __riscv_vfadd_vv_f32mf2(acc, __riscv_vfmul_vv_f32mf2(v2, v3, vl), vl);
    acc = __riscv_vfadd_vv_f32mf2(acc, __riscv_vfmul_vv_f32mf2(v4, v5, vl), vl);
    acc = __riscv_vfsub_vv_f32mf2(acc, v6, vl);
    acc = __riscv_vfadd_vv_f32mf2(acc, v7, vl);
    __riscv_vse32_v_f32mf2(&d[offset], acc, vl);
    return vl;
}
#elif MB3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t v0 = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t v1 = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t v2 = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t v3 = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t v4 = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t v5 = __riscv_vle32_v_f32m1(&x[offset], vl);
    vfloat32m1_t v6 = __riscv_vle32_v_f32m1(&aa[0][offset], vl);
    vfloat32m1_t v7 = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t acc = __riscv_vfadd_vv_f32m1(v0, v1, vl);
    acc = __riscv_vfadd_vv_f32m1(acc, __riscv_vfmul_vv_f32m1(v2, v3, vl), vl);
    acc = __riscv_vfadd_vv_f32m1(acc, __riscv_vfmul_vv_f32m1(v4, v5, vl), vl);
    acc = __riscv_vfsub_vv_f32m1(acc, v6, vl);
    acc = __riscv_vfadd_vv_f32m1(acc, v7, vl);
    __riscv_vse32_v_f32m1(&d[offset], acc, vl);
    return vl;
}
#elif MB3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t v0 = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t v1 = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t v2 = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t v3 = __riscv_vle32_v_f32m2(&d[offset], vl);
    vfloat32m2_t v4 = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t v5 = __riscv_vle32_v_f32m2(&x[offset], vl);
    vfloat32m2_t v6 = __riscv_vle32_v_f32m2(&aa[0][offset], vl);
    vfloat32m2_t v7 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t acc = __riscv_vfadd_vv_f32m2(v0, v1, vl);
    acc = __riscv_vfadd_vv_f32m2(acc, __riscv_vfmul_vv_f32m2(v2, v3, vl), vl);
    acc = __riscv_vfadd_vv_f32m2(acc, __riscv_vfmul_vv_f32m2(v4, v5, vl), vl);
    acc = __riscv_vfsub_vv_f32m2(acc, v6, vl);
    acc = __riscv_vfadd_vv_f32m2(acc, v7, vl);
    __riscv_vse32_v_f32m2(&d[offset], acc, vl);
    return vl;
}
#else
#error "unsupported MB3_VARIANT"
#endif

void kernel(void) {
    (void)MB3_TEMP_COUNT;
    for (int iter = 0; iter < MB3_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
