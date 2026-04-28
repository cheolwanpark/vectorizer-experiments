#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB1_FROM_VARIANT
#define MB1_FROM_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB1_TO_VARIANT
#define MB1_TO_VARIANT DLMUL_LMUL_M4
#endif

#ifndef MB1_FIRST_AVL
#define MB1_FIRST_AVL 64
#endif

#ifndef MB1_SECOND_AVL
#define MB1_SECOND_AVL 64
#endif

#ifndef MB1_OUTER_ITERS
#define MB1_OUTER_ITERS 256
#endif

#if MB1_FROM_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb1_from_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(vb, vc, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif MB1_FROM_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb1_from_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(vb, vc, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#elif MB1_FROM_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb1_from_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], vl);
    vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], vl);
    vfloat32m8_t out = __riscv_vfadd_vv_f32m8(vb, vc, vl);
    __riscv_vse32_v_f32m8(&a[offset], out, vl);
    return vl;
}
#elif MB1_FROM_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb1_from_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf2(avl);
    vfloat32mf2_t vb = __riscv_vle32_v_f32mf2(&b[offset], vl);
    vfloat32mf2_t vc = __riscv_vle32_v_f32mf2(&c[offset], vl);
    vfloat32mf2_t out = __riscv_vfadd_vv_f32mf2(vb, vc, vl);
    __riscv_vse32_v_f32mf2(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB1_FROM_VARIANT"
#endif

#if MB1_TO_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb1_to_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t ve = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t out = __riscv_vfsub_vv_f32m1(vd, ve, vl);
    __riscv_vse32_v_f32m1(&x[offset], out, vl);
    return vl;
}
#elif MB1_TO_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb1_to_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t out = __riscv_vfsub_vv_f32m4(vd, ve, vl);
    __riscv_vse32_v_f32m4(&x[offset], out, vl);
    return vl;
}
#elif MB1_TO_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb1_to_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], vl);
    vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], vl);
    vfloat32m8_t out = __riscv_vfsub_vv_f32m8(vd, ve, vl);
    __riscv_vse32_v_f32m8(&x[offset], out, vl);
    return vl;
}
#elif MB1_TO_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb1_to_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf2(avl);
    vfloat32mf2_t vd = __riscv_vle32_v_f32mf2(&d[offset], vl);
    vfloat32mf2_t ve = __riscv_vle32_v_f32mf2(&e[offset], vl);
    vfloat32mf2_t out = __riscv_vfsub_vv_f32mf2(vd, ve, vl);
    __riscv_vse32_v_f32mf2(&x[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB1_TO_VARIANT"
#endif

void kernel(void) {
    for (int iter = 0; iter < MB1_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB1_FIRST_AVL;
        while (remaining > 0) {
            size_t vl = mb1_from_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = MB1_SECOND_AVL;
        while (remaining > 0) {
            size_t vl = mb1_to_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
