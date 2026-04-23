#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB12_TOTAL_ELEMS 192
#define DB12_OUTER_ITERS 24

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB12_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DB12_TOTAL_ELEMS);
        for (int offset = 0; offset < DB12_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB12_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m1_t dx = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t dy = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t dz = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t vx = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t vy = __riscv_vle32_v_f32m1(&e[offset], avl);
            vfloat32m1_t vz = __riscv_vle32_v_f32m1(&x[offset], avl);
            vfloat32m1_t seed = __riscv_vfmul_vv_f32m1(dx, dx, avl);
            seed = __riscv_vfmacc_vv_f32m1(seed, dy, dy, avl);
            seed = __riscv_vfmacc_vv_f32m1(seed, dz, dz, avl);
            vfloat32m1_t len = __riscv_vfadd_vf_f32m1(seed, 0.03125f, avl);
            len = __riscv_vfsqrt_v_f32m1(len, avl);
            vfloat32m1_t inv = __riscv_vfrdiv_vf_f32m1(len, 1.0f, avl);
            vfloat32m1_t spring = __riscv_vfadd_vf_f32m1(len, -1.25f, avl);
            spring = __riscv_vfmul_vf_f32m1(spring, 0.1875f, avl);
            vfloat32m1_t force = __riscv_vfmul_vv_f32m1(spring, inv, avl);
            vfloat32m1_t fx = __riscv_vfmul_vv_f32m1(force, dx, avl);
            vfloat32m1_t fy = __riscv_vfmul_vv_f32m1(force, dy, avl);
            vfloat32m1_t fz = __riscv_vfmul_vv_f32m1(force, dz, avl);
            vfloat32m1_t vx_out = __riscv_vfmacc_vf_f32m1(vx, 0.0625f, fx, avl);
            vfloat32m1_t vy_out = __riscv_vfmacc_vf_f32m1(vy, 0.0625f, fy, avl);
            vfloat32m1_t vz_out = __riscv_vfmacc_vf_f32m1(vz, 0.0625f, fz, avl);

            __riscv_vse32_v_f32m1(&a[offset], vx_out, avl);
            __riscv_vse32_v_f32m1(&b[offset], vy_out, avl);
            __riscv_vse32_v_f32m1(&c[offset], vz_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB12_TOTAL_ELEMS);
        for (int offset = 0; offset < DB12_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB12_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t dx = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t dy = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t dz = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t vy = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vz = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t seed = __riscv_vfmul_vv_f32m2(dx, dx, avl);
            seed = __riscv_vfmacc_vv_f32m2(seed, dy, dy, avl);
            seed = __riscv_vfmacc_vv_f32m2(seed, dz, dz, avl);
            vfloat32m2_t len = __riscv_vfadd_vf_f32m2(seed, 0.03125f, avl);
            len = __riscv_vfsqrt_v_f32m2(len, avl);
            vfloat32m2_t inv = __riscv_vfrdiv_vf_f32m2(len, 1.0f, avl);
            vfloat32m2_t spring = __riscv_vfadd_vf_f32m2(len, -1.25f, avl);
            spring = __riscv_vfmul_vf_f32m2(spring, 0.1875f, avl);
            vfloat32m2_t force = __riscv_vfmul_vv_f32m2(spring, inv, avl);
            vfloat32m2_t fx = __riscv_vfmul_vv_f32m2(force, dx, avl);
            vfloat32m2_t fy = __riscv_vfmul_vv_f32m2(force, dy, avl);
            vfloat32m2_t fz = __riscv_vfmul_vv_f32m2(force, dz, avl);
            vfloat32m2_t vx_out = __riscv_vfmacc_vf_f32m2(vx, 0.0625f, fx, avl);
            vfloat32m2_t vy_out = __riscv_vfmacc_vf_f32m2(vy, 0.0625f, fy, avl);
            vfloat32m2_t vz_out = __riscv_vfmacc_vf_f32m2(vz, 0.0625f, fz, avl);

            __riscv_vse32_v_f32m2(&a[offset], vx_out, avl);
            __riscv_vse32_v_f32m2(&b[offset], vy_out, avl);
            __riscv_vse32_v_f32m2(&c[offset], vz_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB12_TOTAL_ELEMS);
        for (int offset = 0; offset < DB12_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB12_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m4_t dx = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t dy = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t dz = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t vy = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vz = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t seed = __riscv_vfmul_vv_f32m4(dx, dx, avl);
            seed = __riscv_vfmacc_vv_f32m4(seed, dy, dy, avl);
            seed = __riscv_vfmacc_vv_f32m4(seed, dz, dz, avl);
            vfloat32m4_t len = __riscv_vfadd_vf_f32m4(seed, 0.03125f, avl);
            len = __riscv_vfsqrt_v_f32m4(len, avl);
            vfloat32m4_t inv = __riscv_vfrdiv_vf_f32m4(len, 1.0f, avl);
            vfloat32m4_t spring = __riscv_vfadd_vf_f32m4(len, -1.25f, avl);
            spring = __riscv_vfmul_vf_f32m4(spring, 0.1875f, avl);
            vfloat32m4_t force = __riscv_vfmul_vv_f32m4(spring, inv, avl);
            vfloat32m4_t fx = __riscv_vfmul_vv_f32m4(force, dx, avl);
            vfloat32m4_t fy = __riscv_vfmul_vv_f32m4(force, dy, avl);
            vfloat32m4_t fz = __riscv_vfmul_vv_f32m4(force, dz, avl);
            vfloat32m4_t vx_out = __riscv_vfmacc_vf_f32m4(vx, 0.0625f, fx, avl);
            vfloat32m4_t vy_out = __riscv_vfmacc_vf_f32m4(vy, 0.0625f, fy, avl);
            vfloat32m4_t vz_out = __riscv_vfmacc_vf_f32m4(vz, 0.0625f, fz, avl);

            __riscv_vse32_v_f32m4(&a[offset], vx_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], vy_out, avl);
            __riscv_vse32_v_f32m4(&c[offset], vz_out, avl);
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB12_TOTAL_ELEMS);
        for (int offset = 0; offset < DB12_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB12_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t dx = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t dy = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t dz = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t vy = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vz = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t seed = __riscv_vfmul_vv_f32m4(dx, dx, avl);
            seed = __riscv_vfmacc_vv_f32m4(seed, dy, dy, avl);
            seed = __riscv_vfmacc_vv_f32m4(seed, dz, dz, avl);
            vfloat32m4_t fx = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            vfloat32m4_t fy = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            vfloat32m4_t fz = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define DB12_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xdx = __riscv_vget_v_f32m4_f32m2(dx, (K)); \
        vfloat32m2_t xdy = __riscv_vget_v_f32m4_f32m2(dy, (K)); \
        vfloat32m2_t xdz = __riscv_vget_v_f32m4_f32m2(dz, (K)); \
        vfloat32m2_t xseed = __riscv_vget_v_f32m4_f32m2(seed, (K)); \
        vfloat32m2_t len = __riscv_vfadd_vf_f32m2(xseed, 0.03125f, vlc); \
        len = __riscv_vfsqrt_v_f32m2(len, vlc); \
        vfloat32m2_t inv = __riscv_vfrdiv_vf_f32m2(len, 1.0f, vlc); \
        vfloat32m2_t spring = __riscv_vfadd_vf_f32m2(len, -1.25f, vlc); \
        spring = __riscv_vfmul_vf_f32m2(spring, 0.1875f, vlc); \
        vfloat32m2_t force = __riscv_vfmul_vv_f32m2(spring, inv, vlc); \
        vfloat32m2_t out_x = __riscv_vfmul_vv_f32m2(force, xdx, vlc); \
        vfloat32m2_t out_y = __riscv_vfmul_vv_f32m2(force, xdy, vlc); \
        vfloat32m2_t out_z = __riscv_vfmul_vv_f32m2(force, xdz, vlc); \
        fx = __riscv_vset_v_f32m2_f32m4(fx, (K), out_x); \
        fy = __riscv_vset_v_f32m2_f32m4(fy, (K), out_y); \
        fz = __riscv_vset_v_f32m2_f32m4(fz, (K), out_z); \
    } \
} while (0)
            DB12_CHUNK(0); DB12_CHUNK(1);
#undef DB12_CHUNK
            __riscv_vsetvl_e32m4(avl);
            vfloat32m4_t vx_out = __riscv_vfmacc_vf_f32m4(vx, 0.0625f, fx, avl);
            vfloat32m4_t vy_out = __riscv_vfmacc_vf_f32m4(vy, 0.0625f, fy, avl);
            vfloat32m4_t vz_out = __riscv_vfmacc_vf_f32m4(vz, 0.0625f, fz, avl);

            __riscv_vse32_v_f32m4(&a[offset], vx_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], vy_out, avl);
            __riscv_vse32_v_f32m4(&c[offset], vz_out, avl);
        }
#endif
    }
}
