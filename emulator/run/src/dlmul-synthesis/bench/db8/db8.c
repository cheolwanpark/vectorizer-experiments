#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#ifndef DB8_PRESSURE_REPEATS
#define DB8_PRESSURE_REPEATS 2
#endif

#define DB8_TOTAL_ELEMS 128
#define DB8_OUTER_ITERS 28

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB8_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB8_TOTAL_ELEMS);
        for (int offset = 0; offset < DB8_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB8_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t f0 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], avl);
            vfloat32m2_t f1 = __riscv_vle32_v_f32m2(&flat_2d_array[DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f2 = __riscv_vle32_v_f32m2(&flat_2d_array[2 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f3 = __riscv_vle32_v_f32m2(&flat_2d_array[3 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f4 = __riscv_vle32_v_f32m2(&flat_2d_array[4 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f5 = __riscv_vle32_v_f32m2(&flat_2d_array[5 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t a_out = __riscv_vfadd_vv_f32m2(va, vb, avl);
            vfloat32m2_t b_out = vb;
            for (int repeat = 0; repeat < DB8_PRESSURE_REPEATS; ++repeat) {
                b_out = __riscv_vfadd_vv_f32m2(a_out, b_out, avl);
                b_out = __riscv_vfmacc_vv_f32m2(b_out, vc, vd, avl);
                b_out = __riscv_vfmacc_vv_f32m2(b_out, ve, vx, avl);
                b_out = __riscv_vfmacc_vv_f32m2(b_out, f0, f1, avl);
                b_out = __riscv_vfmacc_vv_f32m2(b_out, f2, f3, avl);
                b_out = __riscv_vfmacc_vv_f32m2(b_out, f4, f5, avl);
            }
            vfloat32m2_t d_out = __riscv_vfmacc_vf_f32m2(a_out, 0.375f, b_out, avl);
            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m2(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m2(&d[offset], d_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB8_TOTAL_ELEMS);
        for (int offset = 0; offset < DB8_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB8_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t f0 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t f1 = __riscv_vle32_v_f32m4(&flat_2d_array[DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f2 = __riscv_vle32_v_f32m4(&flat_2d_array[2 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f3 = __riscv_vle32_v_f32m4(&flat_2d_array[3 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f4 = __riscv_vle32_v_f32m4(&flat_2d_array[4 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f5 = __riscv_vle32_v_f32m4(&flat_2d_array[5 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t b_out = vb;
            for (int repeat = 0; repeat < DB8_PRESSURE_REPEATS; ++repeat) {
                b_out = __riscv_vfadd_vv_f32m4(a_out, b_out, avl);
                b_out = __riscv_vfmacc_vv_f32m4(b_out, vc, vd, avl);
                b_out = __riscv_vfmacc_vv_f32m4(b_out, ve, vx, avl);
                b_out = __riscv_vfmacc_vv_f32m4(b_out, f0, f1, avl);
                b_out = __riscv_vfmacc_vv_f32m4(b_out, f2, f3, avl);
                b_out = __riscv_vfmacc_vv_f32m4(b_out, f4, f5, avl);
            }
            vfloat32m4_t d_out = __riscv_vfmacc_vf_f32m4(a_out, 0.375f, b_out, avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m4(&d[offset], d_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
        size_t vl_base = __riscv_vsetvl_e32m8((size_t)DB8_TOTAL_ELEMS);
        for (int offset = 0; offset < DB8_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB8_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t f0 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t f1 = __riscv_vle32_v_f32m8(&flat_2d_array[DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f2 = __riscv_vle32_v_f32m8(&flat_2d_array[2 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f3 = __riscv_vle32_v_f32m8(&flat_2d_array[3 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f4 = __riscv_vle32_v_f32m8(&flat_2d_array[4 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f5 = __riscv_vle32_v_f32m8(&flat_2d_array[5 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            vfloat32m8_t b_out = vb;
            for (int repeat = 0; repeat < DB8_PRESSURE_REPEATS; ++repeat) {
                b_out = __riscv_vfadd_vv_f32m8(a_out, b_out, avl);
                b_out = __riscv_vfmacc_vv_f32m8(b_out, vc, vd, avl);
                b_out = __riscv_vfmacc_vv_f32m8(b_out, ve, vx, avl);
                b_out = __riscv_vfmacc_vv_f32m8(b_out, f0, f1, avl);
                b_out = __riscv_vfmacc_vv_f32m8(b_out, f2, f3, avl);
                b_out = __riscv_vfmacc_vv_f32m8(b_out, f4, f5, avl);
            }
            vfloat32m8_t d_out = __riscv_vfmacc_vf_f32m8(a_out, 0.375f, b_out, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m8(&d[offset], d_out, avl);
        }
#else
        size_t vl8 = __riscv_vsetvl_e32m8((size_t)DB8_TOTAL_ELEMS);
        for (int offset = 0; offset < DB8_TOTAL_ELEMS; offset += (int)vl8) {
            size_t avl = (size_t)(DB8_TOTAL_ELEMS - offset);
            if (avl > vl8) avl = vl8;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t f0 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t f1 = __riscv_vle32_v_f32m8(&flat_2d_array[DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f2 = __riscv_vle32_v_f32m8(&flat_2d_array[2 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f3 = __riscv_vle32_v_f32m8(&flat_2d_array[3 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f4 = __riscv_vle32_v_f32m8(&flat_2d_array[4 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f5 = __riscv_vle32_v_f32m8(&flat_2d_array[5 * DB8_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            vfloat32m8_t b_out = vb;
            size_t chunk = __riscv_vsetvl_e32m2(avl);
            for (int repeat = 0; repeat < DB8_PRESSURE_REPEATS; ++repeat) {
                vfloat32m8_t next = __riscv_vfmv_v_f_f32m8(0.0f, avl);
#define DB8_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xa = __riscv_vget_v_f32m8_f32m2(a_out, (K)); \
        vfloat32m2_t xb = __riscv_vget_v_f32m8_f32m2(b_out, (K)); \
        vfloat32m2_t xc = __riscv_vget_v_f32m8_f32m2(vc, (K)); \
        vfloat32m2_t xd = __riscv_vget_v_f32m8_f32m2(vd, (K)); \
        vfloat32m2_t xe = __riscv_vget_v_f32m8_f32m2(ve, (K)); \
        vfloat32m2_t xx = __riscv_vget_v_f32m8_f32m2(vx, (K)); \
        vfloat32m2_t x0 = __riscv_vget_v_f32m8_f32m2(f0, (K)); \
        vfloat32m2_t x1 = __riscv_vget_v_f32m8_f32m2(f1, (K)); \
        vfloat32m2_t x2 = __riscv_vget_v_f32m8_f32m2(f2, (K)); \
        vfloat32m2_t x3 = __riscv_vget_v_f32m8_f32m2(f3, (K)); \
        vfloat32m2_t x4 = __riscv_vget_v_f32m8_f32m2(f4, (K)); \
        vfloat32m2_t x5 = __riscv_vget_v_f32m8_f32m2(f5, (K)); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(xa, xb, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, xc, xd, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, xe, xx, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, x0, x1, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, x2, x3, vlc); \
        out = __riscv_vfmacc_vv_f32m2(out, x4, x5, vlc); \
        next = __riscv_vset_v_f32m2_f32m8(next, (K), out); \
    } \
} while (0)
                DB8_CHUNK(0); DB8_CHUNK(1); DB8_CHUNK(2); DB8_CHUNK(3);
#undef DB8_CHUNK
                b_out = next;
            }
            __riscv_vsetvl_e32m8(avl);
            vfloat32m8_t d_out = __riscv_vfmacc_vf_f32m8(a_out, 0.375f, b_out, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m8(&d[offset], d_out, avl);
        }
#endif
    }
}
