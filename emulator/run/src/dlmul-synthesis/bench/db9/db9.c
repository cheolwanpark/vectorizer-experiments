#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M4
#endif

#define DB9_TOTAL_ELEMS 128
#define DB9_OUTER_ITERS 34

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB9_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB9_TOTAL_ELEMS);
        for (int offset = 0; offset < DB9_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB9_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t r = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t g = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t b0 = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t u = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t v = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t k0 = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t k1 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], avl);
            vfloat32m2_t k2 = __riscv_vle32_v_f32m2(&flat_2d_array[DB9_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t y = __riscv_vfadd_vv_f32m2(r, g, avl);
            y = __riscv_vfmacc_vf_f32m2(y, 0.5f, b0, avl);
            vfloat32m2_t y2 = __riscv_vfmul_vv_f32m2(y, y, avl);
            vfloat32m2_t u2 = __riscv_vfmul_vv_f32m2(u, u, avl);
            vfloat32m2_t v2 = __riscv_vfmul_vv_f32m2(v, v, avl);
            vfloat32m2_t p0 = __riscv_vfmacc_vv_f32m2(y, y2, k0, avl);
            vfloat32m2_t p1 = __riscv_vfmacc_vv_f32m2(u, u2, k1, avl);
            vfloat32m2_t p2 = __riscv_vfmacc_vv_f32m2(v, v2, k2, avl);
            vfloat32m2_t gamma = __riscv_vfadd_vv_f32m2(p0, p1, avl);
            gamma = __riscv_vfadd_vv_f32m2(gamma, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m2(gamma, 0.125f, y2, avl);
            vfloat32m2_t c_out = __riscv_vfmacc_vf_f32m2(y, 0.25f, gamma, avl);
            __riscv_vse32_v_f32m2(&a[offset], y, avl);
            __riscv_vse32_v_f32m2(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m2(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB9_TOTAL_ELEMS);
        for (int offset = 0; offset < DB9_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB9_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t r = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t g = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t b0 = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t u = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t v = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t k0 = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t k1 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t k2 = __riscv_vle32_v_f32m4(&flat_2d_array[DB9_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t y = __riscv_vfadd_vv_f32m4(r, g, avl);
            y = __riscv_vfmacc_vf_f32m4(y, 0.5f, b0, avl);
            vfloat32m4_t y2 = __riscv_vfmul_vv_f32m4(y, y, avl);
            vfloat32m4_t u2 = __riscv_vfmul_vv_f32m4(u, u, avl);
            vfloat32m4_t v2 = __riscv_vfmul_vv_f32m4(v, v, avl);
            vfloat32m4_t p0 = __riscv_vfmacc_vv_f32m4(y, y2, k0, avl);
            vfloat32m4_t p1 = __riscv_vfmacc_vv_f32m4(u, u2, k1, avl);
            vfloat32m4_t p2 = __riscv_vfmacc_vv_f32m4(v, v2, k2, avl);
            vfloat32m4_t gamma = __riscv_vfadd_vv_f32m4(p0, p1, avl);
            gamma = __riscv_vfadd_vv_f32m4(gamma, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m4(gamma, 0.125f, y2, avl);
            vfloat32m4_t c_out = __riscv_vfmacc_vf_f32m4(y, 0.25f, gamma, avl);
            __riscv_vse32_v_f32m4(&a[offset], y, avl);
            __riscv_vse32_v_f32m4(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m4(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
        size_t vl_base = __riscv_vsetvl_e32m8((size_t)DB9_TOTAL_ELEMS);
        for (int offset = 0; offset < DB9_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB9_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m8_t r = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t g = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t b0 = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t u = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t v = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t k0 = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t k1 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t k2 = __riscv_vle32_v_f32m8(&flat_2d_array[DB9_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t y = __riscv_vfadd_vv_f32m8(r, g, avl);
            y = __riscv_vfmacc_vf_f32m8(y, 0.5f, b0, avl);
            vfloat32m8_t y2 = __riscv_vfmul_vv_f32m8(y, y, avl);
            vfloat32m8_t u2 = __riscv_vfmul_vv_f32m8(u, u, avl);
            vfloat32m8_t v2 = __riscv_vfmul_vv_f32m8(v, v, avl);
            vfloat32m8_t p0 = __riscv_vfmacc_vv_f32m8(y, y2, k0, avl);
            vfloat32m8_t p1 = __riscv_vfmacc_vv_f32m8(u, u2, k1, avl);
            vfloat32m8_t p2 = __riscv_vfmacc_vv_f32m8(v, v2, k2, avl);
            vfloat32m8_t gamma = __riscv_vfadd_vv_f32m8(p0, p1, avl);
            gamma = __riscv_vfadd_vv_f32m8(gamma, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m8(gamma, 0.125f, y2, avl);
            vfloat32m8_t c_out = __riscv_vfmacc_vf_f32m8(y, 0.25f, gamma, avl);
            __riscv_vse32_v_f32m8(&a[offset], y, avl);
            __riscv_vse32_v_f32m8(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m8(&c[offset], c_out, avl);
        }
#else
        size_t vl8 = __riscv_vsetvl_e32m8((size_t)DB9_TOTAL_ELEMS);
        for (int offset = 0; offset < DB9_TOTAL_ELEMS; offset += (int)vl8) {
            size_t avl = (size_t)(DB9_TOTAL_ELEMS - offset);
            if (avl > vl8) avl = vl8;
            vfloat32m8_t r = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t g = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t b0 = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t u = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t v = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t k0 = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t k1 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t k2 = __riscv_vle32_v_f32m8(&flat_2d_array[DB9_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t y = __riscv_vfadd_vv_f32m8(r, g, avl);
            y = __riscv_vfmacc_vf_f32m8(y, 0.5f, b0, avl);
            vfloat32m8_t gamma = __riscv_vfmv_v_f_f32m8(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define DB9_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xy = __riscv_vget_v_f32m8_f32m2(y, (K)); \
        vfloat32m2_t xu = __riscv_vget_v_f32m8_f32m2(u, (K)); \
        vfloat32m2_t xv = __riscv_vget_v_f32m8_f32m2(v, (K)); \
        vfloat32m2_t xk0 = __riscv_vget_v_f32m8_f32m2(k0, (K)); \
        vfloat32m2_t xk1 = __riscv_vget_v_f32m8_f32m2(k1, (K)); \
        vfloat32m2_t xk2 = __riscv_vget_v_f32m8_f32m2(k2, (K)); \
        vfloat32m2_t y2 = __riscv_vfmul_vv_f32m2(xy, xy, vlc); \
        vfloat32m2_t u2 = __riscv_vfmul_vv_f32m2(xu, xu, vlc); \
        vfloat32m2_t v2 = __riscv_vfmul_vv_f32m2(xv, xv, vlc); \
        vfloat32m2_t p0 = __riscv_vfmacc_vv_f32m2(xy, y2, xk0, vlc); \
        vfloat32m2_t p1 = __riscv_vfmacc_vv_f32m2(xu, u2, xk1, vlc); \
        vfloat32m2_t p2 = __riscv_vfmacc_vv_f32m2(xv, v2, xk2, vlc); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(p0, p1, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, p2, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.125f, y2, vlc); \
        gamma = __riscv_vset_v_f32m2_f32m8(gamma, (K), out); \
    } \
} while (0)
            DB9_CHUNK(0); DB9_CHUNK(1); DB9_CHUNK(2); DB9_CHUNK(3);
#undef DB9_CHUNK
            __riscv_vsetvl_e32m8(avl);
            vfloat32m8_t c_big = __riscv_vfmacc_vf_f32m8(y, 0.25f, gamma, avl);
            size_t store_chunk = __riscv_vsetvl_e32m4(avl);
#define DB9_STORE_CHUNK(K) do { \
    size_t start = (size_t)(K) * store_chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m4(avl - start); \
        vfloat32m4_t part = __riscv_vget_v_f32m8_f32m4(c_big, (K)); \
        __riscv_vse32_v_f32m4(&c[offset + (int)start], part, vlc); \
    } \
} while (0)
            DB9_STORE_CHUNK(0); DB9_STORE_CHUNK(1);
#undef DB9_STORE_CHUNK
            __riscv_vsetvl_e32m8(avl);
            __riscv_vse32_v_f32m8(&a[offset], y, avl);
            __riscv_vse32_v_f32m8(&b[offset], gamma, avl);
        }
#endif
    }
}
