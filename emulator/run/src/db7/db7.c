#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M4
#endif

#define DB7_TOTAL_ELEMS 128
#define DB7_OUTER_ITERS 36

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB7_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB7_TOTAL_ELEMS);
        for (int offset = 0; offset < DB7_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB7_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t f0 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], avl);
            vfloat32m2_t f1 = __riscv_vle32_v_f32m2(&flat_2d_array[DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f2 = __riscv_vle32_v_f32m2(&flat_2d_array[2 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f3 = __riscv_vle32_v_f32m2(&flat_2d_array[3 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f4 = __riscv_vle32_v_f32m2(&flat_2d_array[4 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t f5 = __riscv_vle32_v_f32m2(&flat_2d_array[5 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m2_t a_out = __riscv_vfadd_vv_f32m2(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m2(a_out, 0.1875f, vc, avl);
            vfloat32m2_t acc0 = __riscv_vfmul_vv_f32m2(a_out, vb, avl);
            vfloat32m2_t acc1 = __riscv_vfmul_vv_f32m2(vc, vd, avl);
            vfloat32m2_t acc2 = __riscv_vfmul_vv_f32m2(ve, vx, avl);
            vfloat32m2_t acc3 = __riscv_vfmul_vv_f32m2(f0, f1, avl);
            acc0 = __riscv_vfmacc_vv_f32m2(acc0, f2, f3, avl);
            acc1 = __riscv_vfmacc_vv_f32m2(acc1, f4, f5, avl);
            acc2 = __riscv_vfmacc_vv_f32m2(acc2, a_out, vd, avl);
            acc3 = __riscv_vfmacc_vv_f32m2(acc3, vc, vx, avl);
            vfloat32m2_t b_out = __riscv_vfadd_vv_f32m2(acc0, acc1, avl);
            b_out = __riscv_vfadd_vv_f32m2(b_out, acc2, avl);
            b_out = __riscv_vfadd_vv_f32m2(b_out, acc3, avl);
            vfloat32m2_t c_out = __riscv_vfmacc_vf_f32m2(a_out, 0.5f, b_out, avl);
            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m2(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m2(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB7_TOTAL_ELEMS);
        for (int offset = 0; offset < DB7_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB7_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t f0 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t f1 = __riscv_vle32_v_f32m4(&flat_2d_array[DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f2 = __riscv_vle32_v_f32m4(&flat_2d_array[2 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f3 = __riscv_vle32_v_f32m4(&flat_2d_array[3 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f4 = __riscv_vle32_v_f32m4(&flat_2d_array[4 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t f5 = __riscv_vle32_v_f32m4(&flat_2d_array[5 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.1875f, vc, avl);
            vfloat32m4_t acc0 = __riscv_vfmul_vv_f32m4(a_out, vb, avl);
            vfloat32m4_t acc1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t acc2 = __riscv_vfmul_vv_f32m4(ve, vx, avl);
            vfloat32m4_t acc3 = __riscv_vfmul_vv_f32m4(f0, f1, avl);
            acc0 = __riscv_vfmacc_vv_f32m4(acc0, f2, f3, avl);
            acc1 = __riscv_vfmacc_vv_f32m4(acc1, f4, f5, avl);
            acc2 = __riscv_vfmacc_vv_f32m4(acc2, a_out, vd, avl);
            acc3 = __riscv_vfmacc_vv_f32m4(acc3, vc, vx, avl);
            vfloat32m4_t b_out = __riscv_vfadd_vv_f32m4(acc0, acc1, avl);
            b_out = __riscv_vfadd_vv_f32m4(b_out, acc2, avl);
            b_out = __riscv_vfadd_vv_f32m4(b_out, acc3, avl);
            vfloat32m4_t c_out = __riscv_vfmacc_vf_f32m4(a_out, 0.5f, b_out, avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m4(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
        size_t vl_base = __riscv_vsetvl_e32m8((size_t)DB7_TOTAL_ELEMS);
        for (int offset = 0; offset < DB7_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB7_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t f0 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t f1 = __riscv_vle32_v_f32m8(&flat_2d_array[DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f2 = __riscv_vle32_v_f32m8(&flat_2d_array[2 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f3 = __riscv_vle32_v_f32m8(&flat_2d_array[3 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f4 = __riscv_vle32_v_f32m8(&flat_2d_array[4 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f5 = __riscv_vle32_v_f32m8(&flat_2d_array[5 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.1875f, vc, avl);
            vfloat32m8_t acc0 = __riscv_vfmul_vv_f32m8(a_out, vb, avl);
            vfloat32m8_t acc1 = __riscv_vfmul_vv_f32m8(vc, vd, avl);
            vfloat32m8_t acc2 = __riscv_vfmul_vv_f32m8(ve, vx, avl);
            vfloat32m8_t acc3 = __riscv_vfmul_vv_f32m8(f0, f1, avl);
            acc0 = __riscv_vfmacc_vv_f32m8(acc0, f2, f3, avl);
            acc1 = __riscv_vfmacc_vv_f32m8(acc1, f4, f5, avl);
            acc2 = __riscv_vfmacc_vv_f32m8(acc2, a_out, vd, avl);
            acc3 = __riscv_vfmacc_vv_f32m8(acc3, vc, vx, avl);
            vfloat32m8_t b_out = __riscv_vfadd_vv_f32m8(acc0, acc1, avl);
            b_out = __riscv_vfadd_vv_f32m8(b_out, acc2, avl);
            b_out = __riscv_vfadd_vv_f32m8(b_out, acc3, avl);
            vfloat32m8_t c_out = __riscv_vfmacc_vf_f32m8(a_out, 0.5f, b_out, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m8(&c[offset], c_out, avl);
        }
#else
        size_t vl8 = __riscv_vsetvl_e32m8((size_t)DB7_TOTAL_ELEMS);
        for (int offset = 0; offset < DB7_TOTAL_ELEMS; offset += (int)vl8) {
            size_t avl = (size_t)(DB7_TOTAL_ELEMS - offset);
            if (avl > vl8) avl = vl8;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t f0 = __riscv_vle32_v_f32m8(&flat_2d_array[offset], avl);
            vfloat32m8_t f1 = __riscv_vle32_v_f32m8(&flat_2d_array[DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f2 = __riscv_vle32_v_f32m8(&flat_2d_array[2 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f3 = __riscv_vle32_v_f32m8(&flat_2d_array[3 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f4 = __riscv_vle32_v_f32m8(&flat_2d_array[4 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t f5 = __riscv_vle32_v_f32m8(&flat_2d_array[5 * DB7_TOTAL_ELEMS + offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.1875f, vc, avl);
            vfloat32m8_t b_out = __riscv_vfmv_v_f_f32m8(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define DB7_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xa = __riscv_vget_v_f32m8_f32m2(a_out, (K)); \
        vfloat32m2_t xb = __riscv_vget_v_f32m8_f32m2(vb, (K)); \
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
        vfloat32m2_t acc0 = __riscv_vfmul_vv_f32m2(xa, xb, vlc); \
        vfloat32m2_t acc1 = __riscv_vfmul_vv_f32m2(xc, xd, vlc); \
        vfloat32m2_t acc2 = __riscv_vfmul_vv_f32m2(xe, xx, vlc); \
        vfloat32m2_t acc3 = __riscv_vfmul_vv_f32m2(x0, x1, vlc); \
        acc0 = __riscv_vfmacc_vv_f32m2(acc0, x2, x3, vlc); \
        acc1 = __riscv_vfmacc_vv_f32m2(acc1, x4, x5, vlc); \
        acc2 = __riscv_vfmacc_vv_f32m2(acc2, xa, xd, vlc); \
        acc3 = __riscv_vfmacc_vv_f32m2(acc3, xc, xx, vlc); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(acc0, acc1, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, acc2, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, acc3, vlc); \
        b_out = __riscv_vset_v_f32m2_f32m8(b_out, (K), out); \
    } \
} while (0)
            DB7_CHUNK(0); DB7_CHUNK(1); DB7_CHUNK(2); DB7_CHUNK(3);
#undef DB7_CHUNK
            __riscv_vsetvl_e32m8(avl);
            vfloat32m8_t c_big = __riscv_vfmacc_vf_f32m8(a_out, 0.5f, b_out, avl);
            size_t store_chunk = __riscv_vsetvl_e32m4(avl);
#define DB7_STORE_CHUNK(K) do { \
    size_t start = (size_t)(K) * store_chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m4(avl - start); \
        vfloat32m4_t part = __riscv_vget_v_f32m8_f32m4(c_big, (K)); \
        __riscv_vse32_v_f32m4(&c[offset + (int)start], part, vlc); \
    } \
} while (0)
            DB7_STORE_CHUNK(0); DB7_STORE_CHUNK(1);
#undef DB7_STORE_CHUNK
            __riscv_vsetvl_e32m8(avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
        }
#endif
    }
}
