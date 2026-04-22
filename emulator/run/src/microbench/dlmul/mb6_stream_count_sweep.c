#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB6_SHAPE
#define MB6_SHAPE 1
#endif

#ifndef MB6_LMUL_VARIANT
#define MB6_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB6_TOTAL_ELEMS
#define MB6_TOTAL_ELEMS 256
#endif

#ifndef MB6_OUTER_ITERS
#define MB6_OUTER_ITERS 32
#endif

#if MB6_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb6_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vx = __riscv_vle32_v_f32m1(&b[offset], vl);
#if MB6_SHAPE == 1
    __riscv_vse32_v_f32m1(&a[offset], vx, vl);
#elif MB6_SHAPE == 2
    vfloat32m1_t vy = __riscv_vfmul_vf_f32m1(vx, 1.25f, vl);
    vy = __riscv_vfadd_vf_f32m1(vy, 0.5f, vl);
    __riscv_vse32_v_f32m1(&a[offset], vy, vl);
#elif MB6_SHAPE == 3
    vfloat32m1_t vz = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(vx, vz, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
#elif MB6_SHAPE == 4
    vfloat32m1_t vz = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t out = __riscv_vfmul_vf_f32m1(vx, 1.25f, vl);
    out = __riscv_vfadd_vv_f32m1(out, vz, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
#else
#error "unsupported MB6_SHAPE"
#endif
    return vl;
}
#elif MB6_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb6_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vx = __riscv_vle32_v_f32m4(&b[offset], vl);
#if MB6_SHAPE == 1
    __riscv_vse32_v_f32m4(&a[offset], vx, vl);
#elif MB6_SHAPE == 2
    vfloat32m4_t vy = __riscv_vfmul_vf_f32m4(vx, 1.25f, vl);
    vy = __riscv_vfadd_vf_f32m4(vy, 0.5f, vl);
    __riscv_vse32_v_f32m4(&a[offset], vy, vl);
#elif MB6_SHAPE == 3
    vfloat32m4_t vz = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(vx, vz, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
#elif MB6_SHAPE == 4
    vfloat32m4_t vz = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t out = __riscv_vfmul_vf_f32m4(vx, 1.25f, vl);
    out = __riscv_vfadd_vv_f32m4(out, vz, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
#else
#error "unsupported MB6_SHAPE"
#endif
    return vl;
}
#elif MB6_LMUL_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb6_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t vx = __riscv_vle32_v_f32m8(&b[offset], vl);
#if MB6_SHAPE == 1
    __riscv_vse32_v_f32m8(&a[offset], vx, vl);
#elif MB6_SHAPE == 2
    vfloat32m8_t vy = __riscv_vfmul_vf_f32m8(vx, 1.25f, vl);
    vy = __riscv_vfadd_vf_f32m8(vy, 0.5f, vl);
    __riscv_vse32_v_f32m8(&a[offset], vy, vl);
#elif MB6_SHAPE == 3
    vfloat32m8_t vz = __riscv_vle32_v_f32m8(&c[offset], vl);
    vfloat32m8_t out = __riscv_vfadd_vv_f32m8(vx, vz, vl);
    __riscv_vse32_v_f32m8(&a[offset], out, vl);
#elif MB6_SHAPE == 4
    vfloat32m8_t vz = __riscv_vle32_v_f32m8(&c[offset], vl);
    vfloat32m8_t out = __riscv_vfmul_vf_f32m8(vx, 1.25f, vl);
    out = __riscv_vfadd_vv_f32m8(out, vz, vl);
    __riscv_vse32_v_f32m8(&a[offset], out, vl);
#else
#error "unsupported MB6_SHAPE"
#endif
    return vl;
}
#else
#error "unsupported MB6_LMUL_VARIANT"
#endif

void kernel(void) {
    for (int iter = 0; iter < MB6_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB6_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb6_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
