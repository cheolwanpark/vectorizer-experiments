#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB2_VARIANT
#define MB2_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB2_TOTAL_ELEMS
#define MB2_TOTAL_ELEMS 256
#endif

#ifndef MB2_OUTER_ITERS
#define MB2_OUTER_ITERS 64
#endif

#if MB2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(vb, vc, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif MB2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(vb, vc, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#elif MB2_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], vl);
    vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], vl);
    vfloat32m8_t out = __riscv_vfadd_vv_f32m8(vb, vc, vl);
    __riscv_vse32_v_f32m8(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB2_VARIANT"
#endif

void kernel(void) {
    for (int iter = 0; iter < MB2_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
