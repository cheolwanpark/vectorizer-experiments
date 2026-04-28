#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M2
#endif

#define DB6_TOTAL_ELEMS 192
#define DB6_OUTER_ITERS 32

static int16_t db6_lhs[LEN_1D];
static int16_t db6_rhs[LEN_1D];
static int16_t db6_zp[LEN_1D];
static int32_t db6_bias[LEN_1D];

void kernel(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db6_lhs, db6_rhs, db6_zp, DB6_TOTAL_ELEMS);
    for (int i = 0; i < DB6_TOTAL_ELEMS; ++i) {
        db6_bias[i] = (int32_t)((i % 29) - 14);
    }

    for (int iter = 0; iter < DB6_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DB6_TOTAL_ELEMS);
        for (int offset = 0; offset < DB6_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB6_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t a_out = __riscv_vfadd_vv_f32m1(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m1(a_out, 0.25f, vc, avl);
            a_out = __riscv_vfmacc_vf_f32m1(a_out, 0.125f, vd, avl);
            vint16m1_t lhs = __riscv_vle16_v_i16m1(&db6_lhs[offset], avl);
            vint16m1_t rhs = __riscv_vle16_v_i16m1(&db6_rhs[offset], avl);
            vint16m1_t zp = __riscv_vle16_v_i16m1(&db6_zp[offset], avl);
            vint32m2_t acc0 = __riscv_vwmul_vv_i32m2(lhs, rhs, avl);
            vint32m2_t acc1 = __riscv_vwadd_vv_i32m2(lhs, zp, avl);
            vint32m2_t acc2 = __riscv_vwmul_vv_i32m2(rhs, zp, avl);
            vint32m2_t acc3 = __riscv_vwadd_vv_i32m2(rhs, lhs, avl);
            vint32m2_t acc4 = __riscv_vwmul_vv_i32m2(lhs, lhs, avl);
            vint32m2_t acc5 = __riscv_vwadd_vv_i32m2(rhs, rhs, avl);
            vint32m2_t acc6 = __riscv_vwmul_vv_i32m2(zp, lhs, avl);
            vint32m2_t acc7 = __riscv_vwadd_vv_i32m2(zp, rhs, avl);
            vint32m2_t out = __riscv_vadd_vv_i32m2(acc0, acc1, avl);
            out = __riscv_vadd_vv_i32m2(out, acc2, avl);
            out = __riscv_vadd_vv_i32m2(out, acc3, avl);
            out = __riscv_vadd_vv_i32m2(out, acc4, avl);
            out = __riscv_vadd_vv_i32m2(out, acc5, avl);
            out = __riscv_vadd_vv_i32m2(out, acc6, avl);
            out = __riscv_vadd_vv_i32m2(out, acc7, avl);
            vint32m2_t bias = __riscv_vle32_v_i32m2(&db6_bias[offset], avl);
            out = __riscv_vadd_vv_i32m2(out, bias, avl);
            __riscv_vse32_v_f32m1(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m2(&indx[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB6_TOTAL_ELEMS);
        for (int offset = 0; offset < DB6_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB6_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t a_out = __riscv_vfadd_vv_f32m2(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m2(a_out, 0.25f, vc, avl);
            a_out = __riscv_vfmacc_vf_f32m2(a_out, 0.125f, vd, avl);
            vint16m2_t lhs = __riscv_vle16_v_i16m2(&db6_lhs[offset], avl);
            vint16m2_t rhs = __riscv_vle16_v_i16m2(&db6_rhs[offset], avl);
            vint16m2_t zp = __riscv_vle16_v_i16m2(&db6_zp[offset], avl);
            vint32m4_t acc0 = __riscv_vwmul_vv_i32m4(lhs, rhs, avl);
            vint32m4_t acc1 = __riscv_vwadd_vv_i32m4(lhs, zp, avl);
            vint32m4_t acc2 = __riscv_vwmul_vv_i32m4(rhs, zp, avl);
            vint32m4_t acc3 = __riscv_vwadd_vv_i32m4(rhs, lhs, avl);
            vint32m4_t acc4 = __riscv_vwmul_vv_i32m4(lhs, lhs, avl);
            vint32m4_t acc5 = __riscv_vwadd_vv_i32m4(rhs, rhs, avl);
            vint32m4_t acc6 = __riscv_vwmul_vv_i32m4(zp, lhs, avl);
            vint32m4_t acc7 = __riscv_vwadd_vv_i32m4(zp, rhs, avl);
            vint32m4_t out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            out = __riscv_vadd_vv_i32m4(out, acc2, avl);
            out = __riscv_vadd_vv_i32m4(out, acc3, avl);
            out = __riscv_vadd_vv_i32m4(out, acc4, avl);
            out = __riscv_vadd_vv_i32m4(out, acc5, avl);
            out = __riscv_vadd_vv_i32m4(out, acc6, avl);
            out = __riscv_vadd_vv_i32m4(out, acc7, avl);
            vint32m4_t bias = __riscv_vle32_v_i32m4(&db6_bias[offset], avl);
            out = __riscv_vadd_vv_i32m4(out, bias, avl);
            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB6_TOTAL_ELEMS);
        for (int offset = 0; offset < DB6_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB6_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.25f, vc, avl);
            a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.125f, vd, avl);
            vint16m4_t lhs = __riscv_vle16_v_i16m4(&db6_lhs[offset], avl);
            vint16m4_t rhs = __riscv_vle16_v_i16m4(&db6_rhs[offset], avl);
            vint16m4_t zp = __riscv_vle16_v_i16m4(&db6_zp[offset], avl);
            vint32m8_t acc0 = __riscv_vwmul_vv_i32m8(lhs, rhs, avl);
            vint32m8_t acc1 = __riscv_vwadd_vv_i32m8(lhs, zp, avl);
            vint32m8_t acc2 = __riscv_vwmul_vv_i32m8(rhs, zp, avl);
            vint32m8_t acc3 = __riscv_vwadd_vv_i32m8(rhs, lhs, avl);
            vint32m8_t acc4 = __riscv_vwmul_vv_i32m8(lhs, lhs, avl);
            vint32m8_t acc5 = __riscv_vwadd_vv_i32m8(rhs, rhs, avl);
            vint32m8_t acc6 = __riscv_vwmul_vv_i32m8(zp, lhs, avl);
            vint32m8_t acc7 = __riscv_vwadd_vv_i32m8(zp, rhs, avl);
            vint32m8_t out = __riscv_vadd_vv_i32m8(acc0, acc1, avl);
            out = __riscv_vadd_vv_i32m8(out, acc2, avl);
            out = __riscv_vadd_vv_i32m8(out, acc3, avl);
            out = __riscv_vadd_vv_i32m8(out, acc4, avl);
            out = __riscv_vadd_vv_i32m8(out, acc5, avl);
            out = __riscv_vadd_vv_i32m8(out, acc6, avl);
            out = __riscv_vadd_vv_i32m8(out, acc7, avl);
            vint32m8_t bias = __riscv_vle32_v_i32m8(&db6_bias[offset], avl);
            out = __riscv_vadd_vv_i32m8(out, bias, avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m8(&indx[offset], out, avl);
        }
#else
        size_t vl8 = __riscv_vsetvl_e16m2((size_t)DB6_TOTAL_ELEMS);
        for (int offset = 0; offset < DB6_TOTAL_ELEMS; offset += (int)vl8) {
            size_t avl = (size_t)(DB6_TOTAL_ELEMS - offset);
            if (avl > vl8) avl = vl8;
            vfloat32m8_t va = __riscv_vle32_v_f32m8(&a[offset], avl);
            vfloat32m8_t vb = __riscv_vle32_v_f32m8(&b[offset], avl);
            vfloat32m8_t vc = __riscv_vle32_v_f32m8(&c[offset], avl);
            vfloat32m8_t vd = __riscv_vle32_v_f32m8(&d[offset], avl);
            vfloat32m8_t a_out = __riscv_vfadd_vv_f32m8(va, vb, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.25f, vc, avl);
            a_out = __riscv_vfmacc_vf_f32m8(a_out, 0.125f, vd, avl);
            vint16m2_t lhs = __riscv_vle16_v_i16m2(&db6_lhs[offset], avl);
            vint16m2_t rhs = __riscv_vle16_v_i16m2(&db6_rhs[offset], avl);
            vint16m2_t zp = __riscv_vle16_v_i16m2(&db6_zp[offset], avl);
            vint32m4_t acc0 = __riscv_vwmul_vv_i32m4(lhs, rhs, avl);
            vint32m4_t acc1 = __riscv_vwadd_vv_i32m4(lhs, zp, avl);
            vint32m4_t acc2 = __riscv_vwmul_vv_i32m4(rhs, zp, avl);
            vint32m4_t acc3 = __riscv_vwadd_vv_i32m4(rhs, lhs, avl);
            vint32m4_t acc4 = __riscv_vwmul_vv_i32m4(lhs, lhs, avl);
            vint32m4_t acc5 = __riscv_vwadd_vv_i32m4(rhs, rhs, avl);
            vint32m4_t acc6 = __riscv_vwmul_vv_i32m4(zp, lhs, avl);
            vint32m4_t acc7 = __riscv_vwadd_vv_i32m4(zp, rhs, avl);
            vint32m4_t out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            out = __riscv_vadd_vv_i32m4(out, acc2, avl);
            out = __riscv_vadd_vv_i32m4(out, acc3, avl);
            out = __riscv_vadd_vv_i32m4(out, acc4, avl);
            out = __riscv_vadd_vv_i32m4(out, acc5, avl);
            out = __riscv_vadd_vv_i32m4(out, acc6, avl);
            out = __riscv_vadd_vv_i32m4(out, acc7, avl);
            vint32m4_t bias = __riscv_vle32_v_i32m4(&db6_bias[offset], avl);
            out = __riscv_vadd_vv_i32m4(out, bias, avl);
            __riscv_vse32_v_f32m8(&a[offset], a_out, avl);
#if DLB_BENCH_VARIANT == DLB_VARIANT_DYN_M8_M2_M4
            __riscv_vse32_v_i32m4(&indx[offset], out, avl);
#else
            size_t store_chunk = __riscv_vsetvl_e32m2(avl);
#define DB6_STORE_CHUNK(K) do { \
    size_t start = (size_t)(K) * store_chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vint32m2_t part = __riscv_vget_v_i32m4_i32m2(out, (K)); \
        __riscv_vse32_v_i32m2(&indx[offset + (int)start], part, vlc); \
    } \
} while (0)
            DB6_STORE_CHUNK(0); DB6_STORE_CHUNK(1);
#undef DB6_STORE_CHUNK
#endif
        }
#endif
    }
}
