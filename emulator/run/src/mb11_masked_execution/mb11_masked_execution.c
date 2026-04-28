#include "common.h"
#include "dlmul_variant.h"
#include <riscv_vector.h>

#ifndef MB11_LMUL_VARIANT
#define MB11_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB11_DENSITY
#define MB11_DENSITY 2
#endif

#ifndef MB11_TOTAL_ELEMS
#define MB11_TOTAL_ELEMS 128
#endif

#ifndef MB11_OUTER_ITERS
#define MB11_OUTER_ITERS 24
#endif

#if MB11_DENSITY == 1
#define MB11_THRESHOLD 16
#elif MB11_DENSITY == 2
#define MB11_THRESHOLD 64
#elif MB11_DENSITY == 3
#define MB11_THRESHOLD 112
#else
#error "unsupported MB11_DENSITY"
#endif

#if MB11_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb11_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vint32m1_t vi = __riscv_vle32_v_i32m1(&indx[offset], vl);
    vint32m1_t vj = __riscv_vadd_vx_i32m1(vi, 3, vl);
    vbool32_t mask = __riscv_vmslt_vx_i32m1_b32(vi, MB11_THRESHOLD, vl);
    vint32m1_t out = __riscv_vadd_vv_i32m1_m(mask, vi, vj, vl);
    __riscv_vse32_v_i32m1(&indx[offset], out, vl);
    return vl;
}
#elif MB11_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb11_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t vi = __riscv_vle32_v_i32m4(&indx[offset], vl);
    vint32m4_t vj = __riscv_vadd_vx_i32m4(vi, 3, vl);
    vbool8_t mask = __riscv_vmslt_vx_i32m4_b8(vi, MB11_THRESHOLD, vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4_m(mask, vi, vj, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#elif MB11_LMUL_VARIANT == DLMUL_LMUL_M8
static __attribute__((noinline)) size_t mb11_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m8(avl);
    vint32m8_t vi = __riscv_vle32_v_i32m8(&indx[offset], vl);
    vint32m8_t vj = __riscv_vadd_vx_i32m8(vi, 3, vl);
    vbool4_t mask = __riscv_vmslt_vx_i32m8_b4(vi, MB11_THRESHOLD, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8_m(mask, vi, vj, vl);
    __riscv_vse32_v_i32m8(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB11_LMUL_VARIANT"
#endif

void kernel(void) {
    for (int i = 0; i < MB11_TOTAL_ELEMS; ++i) {
        indx[i] = i;
    }
    for (int iter = 0; iter < MB11_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB11_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb11_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
