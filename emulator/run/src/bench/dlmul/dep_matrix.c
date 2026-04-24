#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#ifndef DLB_DEPENDENCY_MODE
#define DLB_DEPENDENCY_MODE 0
#endif

#define DLB_DEP_MODE_NONE 0
#define DLB_DEP_MODE_13 1
#define DLB_DEP_MODE_12 2
#define DLB_DEP_MODE_13_12 3

#define DEP_TOTAL_ELEMS 192
#define DEP_OUTER_ITERS 32

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DEP_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DEP_TOTAL_ELEMS);
        for (int offset = 0; offset < DEP_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DEP_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t phase1 = __riscv_vfadd_vv_f32m1(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m1(phase1, 0.25f, vc, avl);
            vfloat32m1_t phase1_out = __riscv_vfmacc_vf_f32m1(vb, 0.125f, phase1, avl);

#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_12 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m1_t seed = phase1;
#else
            vfloat32m1_t seed = __riscv_vle32_v_f32m1(&d[offset], avl);
#endif
            vfloat32m1_t s0 = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t s1 = __riscv_vle32_v_f32m1(&e[offset], avl);
            vfloat32m1_t s2 = __riscv_vle32_v_f32m1(&x[offset], avl);
            vfloat32m1_t s3 = __riscv_vle32_v_f32m1(&flat_2d_array[offset], avl);
            vfloat32m1_t s4 = __riscv_vle32_v_f32m1(&flat_2d_array[DEP_TOTAL_ELEMS + offset], avl);
            vfloat32m1_t p0 = __riscv_vfmul_vv_f32m1(seed, seed, avl);
            vfloat32m1_t p1 = __riscv_vfmul_vv_f32m1(s0, s1, avl);
            vfloat32m1_t p2 = __riscv_vfmul_vv_f32m1(s2, s3, avl);
            vfloat32m1_t p3 = __riscv_vfmul_vv_f32m1(seed, s4, avl);
            vfloat32m1_t p4 = __riscv_vfadd_vv_f32m1(p0, p1, avl);
            vfloat32m1_t mid = __riscv_vfadd_vv_f32m1(seed, s0, avl);
            mid = __riscv_vfmacc_vv_f32m1(mid, s1, s2, avl);
            mid = __riscv_vfmacc_vv_f32m1(mid, s3, s4, avl);
            mid = __riscv_vfmacc_vf_f32m1(mid, 0.125f, p2, avl);
            mid = __riscv_vfmacc_vf_f32m1(mid, 0.0625f, p3, avl);
            mid = __riscv_vfmacc_vf_f32m1(mid, 0.03125f, p4, avl);

            vfloat32m1_t tail = __riscv_vle32_v_f32m1(&flat_2d_array[2 * DEP_TOTAL_ELEMS + offset], avl);
#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m1_t base = phase1;
#else
            vfloat32m1_t base = tail;
#endif
            vfloat32m1_t final = __riscv_vfmacc_vf_f32m1(base, 0.25f, mid, avl);
            final = __riscv_vfmacc_vf_f32m1(final, 0.125f, tail, avl);

            __riscv_vse32_v_f32m1(&a[offset], phase1_out, avl);
            __riscv_vse32_v_f32m1(&b[offset], final, avl);
            __riscv_vse32_v_f32m1(&c[offset], mid, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DEP_TOTAL_ELEMS);
        for (int offset = 0; offset < DEP_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DEP_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t phase1 = __riscv_vfadd_vv_f32m2(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m2(phase1, 0.25f, vc, avl);
            vfloat32m2_t phase1_out = __riscv_vfmacc_vf_f32m2(vb, 0.125f, phase1, avl);

#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_12 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m2_t seed = phase1;
#else
            vfloat32m2_t seed = __riscv_vle32_v_f32m2(&d[offset], avl);
#endif
            vfloat32m2_t s0 = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t s1 = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t s2 = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t s3 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], avl);
            vfloat32m2_t s4 = __riscv_vle32_v_f32m2(&flat_2d_array[DEP_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t p0 = __riscv_vfmul_vv_f32m2(seed, seed, avl);
            vfloat32m2_t p1 = __riscv_vfmul_vv_f32m2(s0, s1, avl);
            vfloat32m2_t p2 = __riscv_vfmul_vv_f32m2(s2, s3, avl);
            vfloat32m2_t p3 = __riscv_vfmul_vv_f32m2(seed, s4, avl);
            vfloat32m2_t p4 = __riscv_vfadd_vv_f32m2(p0, p1, avl);
            vfloat32m2_t mid = __riscv_vfadd_vv_f32m2(seed, s0, avl);
            mid = __riscv_vfmacc_vv_f32m2(mid, s1, s2, avl);
            mid = __riscv_vfmacc_vv_f32m2(mid, s3, s4, avl);
            mid = __riscv_vfmacc_vf_f32m2(mid, 0.125f, p2, avl);
            mid = __riscv_vfmacc_vf_f32m2(mid, 0.0625f, p3, avl);
            mid = __riscv_vfmacc_vf_f32m2(mid, 0.03125f, p4, avl);

            vfloat32m2_t tail = __riscv_vle32_v_f32m2(&flat_2d_array[2 * DEP_TOTAL_ELEMS + offset], avl);
#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m2_t base = phase1;
#else
            vfloat32m2_t base = tail;
#endif
            vfloat32m2_t final = __riscv_vfmacc_vf_f32m2(base, 0.25f, mid, avl);
            final = __riscv_vfmacc_vf_f32m2(final, 0.125f, tail, avl);

            __riscv_vse32_v_f32m2(&a[offset], phase1_out, avl);
            __riscv_vse32_v_f32m2(&b[offset], final, avl);
            __riscv_vse32_v_f32m2(&c[offset], mid, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DEP_TOTAL_ELEMS);
        for (int offset = 0; offset < DEP_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DEP_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t phase1 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m4(phase1, 0.25f, vc, avl);
            vfloat32m4_t phase1_out = __riscv_vfmacc_vf_f32m4(vb, 0.125f, phase1, avl);

#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_12 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m4_t seed = phase1;
#else
            vfloat32m4_t seed = __riscv_vle32_v_f32m4(&d[offset], avl);
#endif
            vfloat32m4_t s0 = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t s1 = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t s2 = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t s3 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t s4 = __riscv_vle32_v_f32m4(&flat_2d_array[DEP_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t p0 = __riscv_vfmul_vv_f32m4(seed, seed, avl);
            vfloat32m4_t p1 = __riscv_vfmul_vv_f32m4(s0, s1, avl);
            vfloat32m4_t p2 = __riscv_vfmul_vv_f32m4(s2, s3, avl);
            vfloat32m4_t p3 = __riscv_vfmul_vv_f32m4(seed, s4, avl);
            vfloat32m4_t p4 = __riscv_vfadd_vv_f32m4(p0, p1, avl);
            vfloat32m4_t mid = __riscv_vfadd_vv_f32m4(seed, s0, avl);
            mid = __riscv_vfmacc_vv_f32m4(mid, s1, s2, avl);
            mid = __riscv_vfmacc_vv_f32m4(mid, s3, s4, avl);
            mid = __riscv_vfmacc_vf_f32m4(mid, 0.125f, p2, avl);
            mid = __riscv_vfmacc_vf_f32m4(mid, 0.0625f, p3, avl);
            mid = __riscv_vfmacc_vf_f32m4(mid, 0.03125f, p4, avl);

            vfloat32m4_t tail = __riscv_vle32_v_f32m4(&flat_2d_array[2 * DEP_TOTAL_ELEMS + offset], avl);
#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m4_t base = phase1;
#else
            vfloat32m4_t base = tail;
#endif
            vfloat32m4_t final = __riscv_vfmacc_vf_f32m4(base, 0.25f, mid, avl);
            final = __riscv_vfmacc_vf_f32m4(final, 0.125f, tail, avl);

            __riscv_vse32_v_f32m4(&a[offset], phase1_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], final, avl);
            __riscv_vse32_v_f32m4(&c[offset], mid, avl);
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DEP_TOTAL_ELEMS);
        for (int offset = 0; offset < DEP_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DEP_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t phase1 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m4(phase1, 0.25f, vc, avl);
            vfloat32m4_t phase1_out = __riscv_vfmacc_vf_f32m4(vb, 0.125f, phase1, avl);
            vfloat32m4_t mid = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);

#define DEP_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t seed; \
        if (DLB_DEPENDENCY_MODE == DLB_DEP_MODE_12 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12) { \
            seed = __riscv_vget_v_f32m4_f32m2(phase1, (K)); \
        } else { \
            seed = __riscv_vle32_v_f32m2(&d[offset + (int)start], vlc); \
        } \
        vfloat32m2_t s0 = __riscv_vle32_v_f32m2(&d[offset + (int)start], vlc); \
        vfloat32m2_t s1 = __riscv_vle32_v_f32m2(&e[offset + (int)start], vlc); \
        vfloat32m2_t s2 = __riscv_vle32_v_f32m2(&x[offset + (int)start], vlc); \
        vfloat32m2_t s3 = __riscv_vle32_v_f32m2(&flat_2d_array[offset + (int)start], vlc); \
        vfloat32m2_t s4 = __riscv_vle32_v_f32m2(&flat_2d_array[DEP_TOTAL_ELEMS + offset + (int)start], vlc); \
        vfloat32m2_t p0 = __riscv_vfmul_vv_f32m2(seed, seed, vlc); \
        vfloat32m2_t p1 = __riscv_vfmul_vv_f32m2(s0, s1, vlc); \
        vfloat32m2_t p2 = __riscv_vfmul_vv_f32m2(s2, s3, vlc); \
        vfloat32m2_t p3 = __riscv_vfmul_vv_f32m2(seed, s4, vlc); \
        vfloat32m2_t p4 = __riscv_vfadd_vv_f32m2(p0, p1, vlc); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(seed, s0, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, s1, s2, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, s3, s4, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.125f, p2, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.0625f, p3, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.03125f, p4, vlc); \
        mid = __riscv_vset_v_f32m2_f32m4(mid, (K), out); \
    } \
} while (0)
            DEP_CHUNK(0);
            DEP_CHUNK(1);
#undef DEP_CHUNK

            __riscv_vsetvl_e32m4(avl);
            vfloat32m4_t tail = __riscv_vle32_v_f32m4(&flat_2d_array[2 * DEP_TOTAL_ELEMS + offset], avl);
#if DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13 || DLB_DEPENDENCY_MODE == DLB_DEP_MODE_13_12
            vfloat32m4_t base = phase1;
#else
            vfloat32m4_t base = tail;
#endif
            vfloat32m4_t final = __riscv_vfmacc_vf_f32m4(base, 0.25f, mid, avl);
            final = __riscv_vfmacc_vf_f32m4(final, 0.125f, tail, avl);

            __riscv_vse32_v_f32m4(&a[offset], phase1_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], final, avl);
            __riscv_vse32_v_f32m4(&c[offset], mid, avl);
        }
#endif
    }
}
