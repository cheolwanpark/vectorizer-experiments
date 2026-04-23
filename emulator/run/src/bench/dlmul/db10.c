#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#define DB10_TOTAL_ELEMS 224
#define DB10_OUTER_ITERS 32

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < DB10_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB10_TOTAL_ELEMS);
        for (int offset = 0; offset < DB10_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB10_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t a_out = __riscv_vfadd_vv_f32m2(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m2(a_out, 0.125f, va, avl);
            vfloat32m2_t b_out = __riscv_vfadd_vv_f32m2(vc, vd, avl);
            b_out = __riscv_vfmacc_vf_f32m2(b_out, 0.125f, vc, avl);
            vfloat32m2_t c_out = __riscv_vfadd_vv_f32m2(ve, vx, avl);
            c_out = __riscv_vfmacc_vf_f32m2(c_out, 0.125f, ve, avl);
            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m2(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m2(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB10_TOTAL_ELEMS);
        for (int offset = 0; offset < DB10_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB10_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.125f, va, avl);
            vfloat32m4_t b_out = __riscv_vfadd_vv_f32m4(vc, vd, avl);
            b_out = __riscv_vfmacc_vf_f32m4(b_out, 0.125f, vc, avl);
            vfloat32m4_t c_out = __riscv_vfadd_vv_f32m4(ve, vx, avl);
            c_out = __riscv_vfmacc_vf_f32m4(c_out, 0.125f, ve, avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m4(&c[offset], c_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
        size_t vl_base = __riscv_vsetvl_e32m8((size_t)DB10_TOTAL_ELEMS);
        for (int offset = 0; offset < DB10_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB10_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.125f, va, avl);
            vfloat32m8_t b_out = __riscv_vfadd_vv_f32m8(vc, vd, avl);
            b_out = __riscv_vfmacc_vf_f32m8(b_out, 0.125f, vc, avl);
            vfloat32m8_t c_out = __riscv_vfadd_vv_f32m8(ve, vx, avl);
            c_out = __riscv_vfmacc_vf_f32m8(c_out, 0.125f, ve, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m8(&c[offset], c_out, avl);
        }
#else
        size_t vl8 = __riscv_vsetvl_e32m8((size_t)DB10_TOTAL_ELEMS);
        for (int offset = 0; offset < DB10_TOTAL_ELEMS; offset += (int)vl8) {
            size_t avl = (size_t)(DB10_TOTAL_ELEMS - offset);
            if (avl > vl8) avl = vl8;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t ve = __riscv_vle32_v_f32m8(&e[offset], avl);
            vfloat32m8_t vx = __riscv_vle32_v_f32m8(&x[offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.125f, va, avl);
            vfloat32m8_t b_out = __riscv_vfmv_v_f_f32m8(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define DB10_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xc = __riscv_vget_v_f32m8_f32m2(vc, (K)); \
        vfloat32m2_t xd = __riscv_vget_v_f32m8_f32m2(vd, (K)); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(xc, xd, vlc); \
        out = __riscv_vfmacc_vf_f32m2(out, 0.125f, xc, vlc); \
        b_out = __riscv_vset_v_f32m2_f32m8(b_out, (K), out); \
    } \
} while (0)
            DB10_CHUNK(0); DB10_CHUNK(1); DB10_CHUNK(2); DB10_CHUNK(3);
#undef DB10_CHUNK
            __riscv_vsetvl_e32m8(avl);
            vfloat32m8_t c_out = __riscv_vfadd_vv_f32m8(ve, vx, avl);
            c_out = __riscv_vfmacc_vf_f32m8(c_out, 0.125f, ve, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m8(&b[offset], b_out, avl);
            __riscv_vse32_v_f32m8(&c[offset], c_out, avl);
        }
#endif
    }
}
