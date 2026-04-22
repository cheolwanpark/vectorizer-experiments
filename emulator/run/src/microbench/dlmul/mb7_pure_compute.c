#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB7_OP
#define MB7_OP 1
#endif

#ifndef MB7_LMUL_VARIANT
#define MB7_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB7_TOTAL_ELEMS
#define MB7_TOTAL_ELEMS 128
#endif

#ifndef MB7_CHAIN_DEPTH
#define MB7_CHAIN_DEPTH 32
#endif

#ifndef MB7_OUTER_ITERS
#define MB7_OUTER_ITERS 16
#endif

#if MB7_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb7_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t acc = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t x = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t y = __riscv_vle32_v_f32m1(&c[offset], vl);
    for (int i = 0; i < MB7_CHAIN_DEPTH; ++i) {
#if MB7_OP == 1
        acc = __riscv_vfadd_vv_f32m1(acc, x, vl);
#elif MB7_OP == 2
        acc = __riscv_vfmacc_vv_f32m1(acc, x, y, vl);
#else
#error "unsupported MB7_OP"
#endif
    }
    __riscv_vse32_v_f32m1(&d[offset], acc, vl);
    return vl;
}
#elif MB7_LMUL_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb7_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t acc = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t x = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t y = __riscv_vle32_v_f32m2(&c[offset], vl);
    for (int i = 0; i < MB7_CHAIN_DEPTH; ++i) {
#if MB7_OP == 1
        acc = __riscv_vfadd_vv_f32m2(acc, x, vl);
#elif MB7_OP == 2
        acc = __riscv_vfmacc_vv_f32m2(acc, x, y, vl);
#else
#error "unsupported MB7_OP"
#endif
    }
    __riscv_vse32_v_f32m2(&d[offset], acc, vl);
    return vl;
}
#elif MB7_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb7_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t acc = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t y = __riscv_vle32_v_f32m4(&c[offset], vl);
    for (int i = 0; i < MB7_CHAIN_DEPTH; ++i) {
#if MB7_OP == 1
        acc = __riscv_vfadd_vv_f32m4(acc, x, vl);
#elif MB7_OP == 2
        acc = __riscv_vfmacc_vv_f32m4(acc, x, y, vl);
#else
#error "unsupported MB7_OP"
#endif
    }
    __riscv_vse32_v_f32m4(&d[offset], acc, vl);
    return vl;
}
#elif MB7_LMUL_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb7_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t acc = __riscv_vle32_v_f32m8(&a[offset], vl);
    vfloat32m8_t x = __riscv_vle32_v_f32m8(&b[offset], vl);
    vfloat32m8_t y = __riscv_vle32_v_f32m8(&c[offset], vl);
    for (int i = 0; i < MB7_CHAIN_DEPTH; ++i) {
#if MB7_OP == 1
        acc = __riscv_vfadd_vv_f32m8(acc, x, vl);
#elif MB7_OP == 2
        acc = __riscv_vfmacc_vv_f32m8(acc, x, y, vl);
#else
#error "unsupported MB7_OP"
#endif
    }
    __riscv_vse32_v_f32m8(&d[offset], acc, vl);
    return vl;
}
#else
#error "unsupported MB7_LMUL_VARIANT"
#endif

void kernel(void) {
    for (int iter = 0; iter < MB7_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB7_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb7_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
