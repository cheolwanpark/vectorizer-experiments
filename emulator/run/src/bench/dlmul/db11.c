#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB11_TOTAL_ELEMS 192
#define DB11_OUTER_ITERS 34

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB11_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DB11_TOTAL_ELEMS);
        for (int offset = 0; offset < DB11_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB11_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m1_t r = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t g = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t b0 = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t u = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t v = __riscv_vle32_v_f32m1(&e[offset], avl);
            vfloat32m1_t k0 = __riscv_vle32_v_f32m1(&x[offset], avl);
            vfloat32m1_t k1 = __riscv_vle32_v_f32m1(&flat_2d_array[offset], avl);
            vfloat32m1_t y = __riscv_vfmacc_vf_f32m1(r, 0.5f, g, avl);
            y = __riscv_vfmacc_vf_f32m1(y, 0.25f, b0, avl);
            vfloat32m1_t p0 = __riscv_vfmul_vv_f32m1(y, y, avl);
            vfloat32m1_t p1 = __riscv_vfmul_vv_f32m1(u, u, avl);
            vfloat32m1_t p2 = __riscv_vfmul_vv_f32m1(v, v, avl);
            vfloat32m1_t p3 = __riscv_vfmul_vv_f32m1(y, u, avl);
            vfloat32m1_t p4 = __riscv_vfadd_vv_f32m1(p0, p1, avl);
            vfloat32m1_t gamma = __riscv_vfmacc_vv_f32m1(y, p0, k0, avl);
            gamma = __riscv_vfmacc_vv_f32m1(gamma, p1, k1, avl);
            gamma = __riscv_vfmacc_vf_f32m1(gamma, 0.125f, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m1(gamma, 0.0625f, p3, avl);
            gamma = __riscv_vfmacc_vf_f32m1(gamma, 0.03125f, p4, avl);
            vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(y, 0.25f, gamma, avl);

            __riscv_vse32_v_f32m1(&a[offset], y, avl);
            __riscv_vse32_v_f32m1(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m1(&c[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB11_TOTAL_ELEMS);
        for (int offset = 0; offset < DB11_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB11_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t r = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t g = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t b0 = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t u = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t v = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t k0 = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t k1 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], avl);
            vfloat32m2_t y = __riscv_vfmacc_vf_f32m2(r, 0.5f, g, avl);
            y = __riscv_vfmacc_vf_f32m2(y, 0.25f, b0, avl);
            vfloat32m2_t p0 = __riscv_vfmul_vv_f32m2(y, y, avl);
            vfloat32m2_t p1 = __riscv_vfmul_vv_f32m2(u, u, avl);
            vfloat32m2_t p2 = __riscv_vfmul_vv_f32m2(v, v, avl);
            vfloat32m2_t p3 = __riscv_vfmul_vv_f32m2(y, u, avl);
            vfloat32m2_t p4 = __riscv_vfadd_vv_f32m2(p0, p1, avl);
            vfloat32m2_t gamma = __riscv_vfmacc_vv_f32m2(y, p0, k0, avl);
            gamma = __riscv_vfmacc_vv_f32m2(gamma, p1, k1, avl);
            gamma = __riscv_vfmacc_vf_f32m2(gamma, 0.125f, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m2(gamma, 0.0625f, p3, avl);
            gamma = __riscv_vfmacc_vf_f32m2(gamma, 0.03125f, p4, avl);
            vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(y, 0.25f, gamma, avl);

            __riscv_vse32_v_f32m2(&a[offset], y, avl);
            __riscv_vse32_v_f32m2(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m2(&c[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB11_TOTAL_ELEMS);
        for (int offset = 0; offset < DB11_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB11_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m4_t r = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t g = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t b0 = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t u = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t v = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t k0 = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t k1 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t y = __riscv_vfmacc_vf_f32m4(r, 0.5f, g, avl);
            y = __riscv_vfmacc_vf_f32m4(y, 0.25f, b0, avl);
            vfloat32m4_t p0 = __riscv_vfmul_vv_f32m4(y, y, avl);
            vfloat32m4_t p1 = __riscv_vfmul_vv_f32m4(u, u, avl);
            vfloat32m4_t p2 = __riscv_vfmul_vv_f32m4(v, v, avl);
            vfloat32m4_t p3 = __riscv_vfmul_vv_f32m4(y, u, avl);
            vfloat32m4_t p4 = __riscv_vfadd_vv_f32m4(p0, p1, avl);
            vfloat32m4_t gamma = __riscv_vfmacc_vv_f32m4(y, p0, k0, avl);
            gamma = __riscv_vfmacc_vv_f32m4(gamma, p1, k1, avl);
            gamma = __riscv_vfmacc_vf_f32m4(gamma, 0.125f, p2, avl);
            gamma = __riscv_vfmacc_vf_f32m4(gamma, 0.0625f, p3, avl);
            gamma = __riscv_vfmacc_vf_f32m4(gamma, 0.03125f, p4, avl);
            vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(y, 0.25f, gamma, avl);

            __riscv_vse32_v_f32m4(&a[offset], y, avl);
            __riscv_vse32_v_f32m4(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m4(&c[offset], out, avl);
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB11_TOTAL_ELEMS);
        for (int offset = 0; offset < DB11_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB11_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t r = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t g = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t b0 = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t u = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t v = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t k0 = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t k1 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t y = __riscv_vfmacc_vf_f32m4(r, 0.5f, g, avl);
            y = __riscv_vfmacc_vf_f32m4(y, 0.25f, b0, avl);
            vfloat32m4_t gamma = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define DB11_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xy = __riscv_vget_v_f32m4_f32m2(y, (K)); \
        vfloat32m2_t xu = __riscv_vget_v_f32m4_f32m2(u, (K)); \
        vfloat32m2_t xv = __riscv_vget_v_f32m4_f32m2(v, (K)); \
        vfloat32m2_t xk0 = __riscv_vget_v_f32m4_f32m2(k0, (K)); \
        vfloat32m2_t xk1 = __riscv_vget_v_f32m4_f32m2(k1, (K)); \
        vfloat32m2_t p0 = __riscv_vfmul_vv_f32m2(xy, xy, vlc); \
        vfloat32m2_t p1 = __riscv_vfmul_vv_f32m2(xu, xu, vlc); \
        vfloat32m2_t p2 = __riscv_vfmul_vv_f32m2(xv, xv, vlc); \
        vfloat32m2_t p3 = __riscv_vfmul_vv_f32m2(xy, xu, vlc); \
        vfloat32m2_t p4 = __riscv_vfadd_vv_f32m2(p0, p1, vlc); \
        vfloat32m2_t out = __riscv_vfmacc_vv_f32m2(xy, p0, xk0, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, p1, xk1, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.125f, p2, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.0625f, p3, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.03125f, p4, vlc); \
        gamma = __riscv_vset_v_f32m2_f32m4(gamma, (K), out); \
    } \
} while (0)
            DB11_CHUNK(0); DB11_CHUNK(1);
#undef DB11_CHUNK
            __riscv_vsetvl_e32m4(avl);
            vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(y, 0.25f, gamma, avl);

            __riscv_vse32_v_f32m4(&a[offset], y, avl);
            __riscv_vse32_v_f32m4(&b[offset], gamma, avl);
            __riscv_vse32_v_f32m4(&c[offset], out, avl);
        }
#endif
    }
}
