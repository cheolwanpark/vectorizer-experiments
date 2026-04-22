#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB9_PATTERN
#define MB9_PATTERN 1
#endif

#ifndef MB9_PHASE1_TOTAL_ELEMS
#define MB9_PHASE1_TOTAL_ELEMS 128
#endif

#ifndef MB9_PHASE2_TOTAL_ELEMS
#define MB9_PHASE2_TOTAL_ELEMS 64
#endif

#ifndef MB9_OUTER_ITERS
#define MB9_OUTER_ITERS 24
#endif

#if MB9_PATTERN == 1
#define MB9_PHASE1_LMUL DLMUL_LMUL_M8
#define MB9_PHASE2_LMUL DLMUL_LMUL_M1
#elif MB9_PATTERN == 2
#define MB9_PHASE1_LMUL DLMUL_LMUL_M4
#define MB9_PHASE2_LMUL DLMUL_LMUL_MF2
#else
#error "unsupported MB9_PATTERN"
#endif

#if MB9_PHASE1_LMUL == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], vl);
    vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], vl);
    vfloat32m8_t out = __riscv_vfadd_vv_f32m8(va, vb, vl);
    __riscv_vse32_v_f32m8(&d[offset], out, vl);
    return vl;
}
#elif MB9_PHASE1_LMUL == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(va, vb, vl);
    __riscv_vse32_v_f32m4(&d[offset], out, vl);
    return vl;
}
#endif

#if MB9_PHASE2_LMUL == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], vl);
    vfloat32m1_t ve = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t out = __riscv_vfmacc_vv_f32m1(vd, ve, vc, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[offset], out, vl);
    return vl;
}
#elif MB9_PHASE2_LMUL == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf2(avl);
    vfloat32mf2_t vd = __riscv_vle32_v_f32mf2(&d[offset], vl);
    vfloat32mf2_t ve = __riscv_vle32_v_f32mf2(&e[offset], vl);
    vfloat32mf2_t vc = __riscv_vle32_v_f32mf2(&c[offset], vl);
    vfloat32mf2_t out = __riscv_vfmacc_vv_f32mf2(vd, ve, vc, vl);
    __riscv_vse32_v_f32mf2(&flat_2d_array[offset], out, vl);
    return vl;
}
#endif

#if MB9_PHASE1_LMUL == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], vl);
    vfloat32m8_t vt = __riscv_vle32_v_f32m8(&flat_2d_array[offset], vl);
    vfloat32m8_t out = __riscv_vfadd_vv_f32m8(vd, vt, vl);
    __riscv_vse32_v_f32m8(&e[offset], out, vl);
    return vl;
}
#elif MB9_PHASE1_LMUL == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t vt = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(vd, vt, vl);
    __riscv_vse32_v_f32m4(&e[offset], out, vl);
    return vl;
}
#endif

void kernel(void) {
    for (int iter = 0; iter < MB9_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB9_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb9_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
        offset = 0;
        remaining = MB9_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb9_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
        offset = 0;
        remaining = MB9_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb9_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
