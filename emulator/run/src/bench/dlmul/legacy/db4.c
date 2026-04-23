#include "../dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB4_TOTAL_ELEMS 192
#define DB4_OUTER_ITERS 30

static int16_t db4_lhs[LEN_1D];
static int16_t db4_rhs[LEN_1D];
static int16_t db4_zp[LEN_1D];
static int32_t db4_bias[LEN_1D];

void kernel(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db4_lhs, db4_rhs, db4_zp, DB4_TOTAL_ELEMS);
    for (int i = 0; i < DB4_TOTAL_ELEMS; ++i) {
        db4_bias[i] = (int32_t)((i % 23) - 11);
    }

    for (int iter = 0; iter < DB4_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DB4_TOTAL_ELEMS);
        for (int offset = 0; offset < DB4_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB4_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m1_t scale = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t fbias = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t a_out = __riscv_vfmacc_vf_f32m1(scale, 0.5f, fbias, avl);
            vint16m1_t lhs = __riscv_vle16_v_i16m1(&db4_lhs[offset], avl);
            vint16m1_t rhs = __riscv_vle16_v_i16m1(&db4_rhs[offset], avl);
            vint16m1_t zp = __riscv_vle16_v_i16m1(&db4_zp[offset], avl);
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
            vint32m2_t ibias = __riscv_vle32_v_i32m2(&db4_bias[offset], avl);
            out = __riscv_vadd_vv_i32m2(out, ibias, avl);
            __riscv_vse32_v_f32m1(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m2(&indx[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB4_TOTAL_ELEMS);
        for (int offset = 0; offset < DB4_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB4_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m2_t scale = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t fbias = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t a_out = __riscv_vfmacc_vf_f32m2(scale, 0.5f, fbias, avl);
            vint16m2_t lhs = __riscv_vle16_v_i16m2(&db4_lhs[offset], avl);
            vint16m2_t rhs = __riscv_vle16_v_i16m2(&db4_rhs[offset], avl);
            vint16m2_t zp = __riscv_vle16_v_i16m2(&db4_zp[offset], avl);
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
            vint32m4_t ibias = __riscv_vle32_v_i32m4(&db4_bias[offset], avl);
            out = __riscv_vadd_vv_i32m4(out, ibias, avl);
            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB4_TOTAL_ELEMS);
        for (int offset = 0; offset < DB4_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB4_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            vfloat32m4_t scale = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t fbias = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t a_out = __riscv_vfmacc_vf_f32m4(scale, 0.5f, fbias, avl);
            vint16m4_t lhs = __riscv_vle16_v_i16m4(&db4_lhs[offset], avl);
            vint16m4_t rhs = __riscv_vle16_v_i16m4(&db4_rhs[offset], avl);
            vint16m4_t zp = __riscv_vle16_v_i16m4(&db4_zp[offset], avl);
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
            vint32m8_t ibias = __riscv_vle32_v_i32m8(&db4_bias[offset], avl);
            out = __riscv_vadd_vv_i32m8(out, ibias, avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m8(&indx[offset], out, avl);
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB4_TOTAL_ELEMS);
        for (int offset = 0; offset < DB4_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB4_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;
            vfloat32m4_t scale = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t fbias = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t a_out = __riscv_vfmacc_vf_f32m4(scale, 0.5f, fbias, avl);
            vint16m2_t lhs = __riscv_vle16_v_i16m2(&db4_lhs[offset], avl);
            vint16m2_t rhs = __riscv_vle16_v_i16m2(&db4_rhs[offset], avl);
            vint16m2_t zp = __riscv_vle16_v_i16m2(&db4_zp[offset], avl);
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
            vint32m4_t ibias = __riscv_vle32_v_i32m4(&db4_bias[offset], avl);
            out = __riscv_vadd_vv_i32m4(out, ibias, avl);
            __riscv_vsetvl_e32m4(avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], out, avl);
        }
#endif
    }
}
