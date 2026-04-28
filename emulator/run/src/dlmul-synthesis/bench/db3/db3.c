#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#ifndef DB3_PHASE_B_ELEMS
#define DB3_PHASE_B_ELEMS 96
#endif

#define DB3_WIDE_ELEMS 128
#define DB3_TOTAL_ELEMS ((DB3_PHASE_B_ELEMS > DB3_WIDE_ELEMS) ? DB3_PHASE_B_ELEMS : DB3_WIDE_ELEMS)
#define DB3_OUTER_ITERS 32

static int16_t db3_src0[LEN_1D];
static int16_t db3_src1[LEN_1D];
static int16_t db3_bias[LEN_1D];

void kernel(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db3_src0, db3_src1, db3_bias, DB3_PHASE_B_ELEMS);

    for (int iter = 0; iter < DB3_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB3_TOTAL_ELEMS);
        for (int offset = 0; offset < DB3_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB3_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            if (offset < DB3_WIDE_ELEMS) {
                size_t favl = (size_t)(DB3_WIDE_ELEMS - offset);
                if (favl > avl) favl = avl;
                vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], favl);
                vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], favl);
                vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], favl);
                vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], favl);
                vfloat32m2_t a_out = __riscv_vfadd_vv_f32m2(va, vb, favl);
                a_out = __riscv_vfmacc_vf_f32m2(a_out, 0.25f, vc, favl);
                vfloat32m2_t d_out = __riscv_vfmacc_vf_f32m2(a_out, 0.125f, vx, favl);
                __riscv_vse32_v_f32m2(&a[offset], a_out, favl);
                __riscv_vse32_v_f32m2(&d[offset], d_out, favl);
            }
            if (offset < DB3_PHASE_B_ELEMS) {
                size_t iavl = (size_t)(DB3_PHASE_B_ELEMS - offset);
                if (iavl > avl) iavl = avl;
                vint16m2_t x0 = __riscv_vle16_v_i16m2(&db3_src0[offset], iavl);
                vint16m2_t x1 = __riscv_vle16_v_i16m2(&db3_src1[offset], iavl);
                vint16m2_t xb = __riscv_vle16_v_i16m2(&db3_bias[offset], iavl);
                vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, iavl);
                vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, iavl);
                vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, iavl);
                vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, iavl);
                vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, iavl);
                vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, iavl);
                vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, iavl);
                vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, iavl);
                vint32m4_t out = __riscv_vadd_vv_i32m4(acc0, acc1, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc2, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc3, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc4, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc5, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc6, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc7, iavl);
                __riscv_vse32_v_i32m4(&indx[offset], out, iavl);
            }
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB3_TOTAL_ELEMS);
        for (int offset = 0; offset < DB3_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB3_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;
            if (offset < DB3_WIDE_ELEMS) {
                size_t favl = (size_t)(DB3_WIDE_ELEMS - offset);
                if (favl > avl) favl = avl;
                vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], favl);
                vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], favl);
                vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], favl);
                vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], favl);
                vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, favl);
                a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.25f, vc, favl);
                vfloat32m4_t d_out = __riscv_vfmacc_vf_f32m4(a_out, 0.125f, vx, favl);
                __riscv_vse32_v_f32m4(&a[offset], a_out, favl);
                __riscv_vse32_v_f32m4(&d[offset], d_out, favl);
            }
            if (offset < DB3_PHASE_B_ELEMS) {
                size_t iavl = (size_t)(DB3_PHASE_B_ELEMS - offset);
                if (iavl > avl) iavl = avl;
                vint16m4_t x0 = __riscv_vle16_v_i16m4(&db3_src0[offset], iavl);
                vint16m4_t x1 = __riscv_vle16_v_i16m4(&db3_src1[offset], iavl);
                vint16m4_t xb = __riscv_vle16_v_i16m4(&db3_bias[offset], iavl);
                vint32m8_t acc0 = __riscv_vwadd_vv_i32m8(x0, x1, iavl);
                vint32m8_t acc1 = __riscv_vwmul_vv_i32m8(x0, x1, iavl);
                vint32m8_t acc2 = __riscv_vwadd_vv_i32m8(x1, xb, iavl);
                vint32m8_t acc3 = __riscv_vwmul_vv_i32m8(x1, xb, iavl);
                vint32m8_t acc4 = __riscv_vwadd_vv_i32m8(x0, xb, iavl);
                vint32m8_t acc5 = __riscv_vwmul_vv_i32m8(x0, xb, iavl);
                vint32m8_t acc6 = __riscv_vwadd_vv_i32m8(xb, x1, iavl);
                vint32m8_t acc7 = __riscv_vwmul_vv_i32m8(xb, x0, iavl);
                vint32m8_t out = __riscv_vadd_vv_i32m8(acc0, acc1, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc2, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc3, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc4, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc5, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc6, iavl);
                out = __riscv_vadd_vv_i32m8(out, acc7, iavl);
                __riscv_vse32_v_i32m8(&indx[offset], out, iavl);
            }
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB3_TOTAL_ELEMS);
        for (int offset = 0; offset < DB3_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB3_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;
            if (offset < DB3_WIDE_ELEMS) {
                size_t favl = (size_t)(DB3_WIDE_ELEMS - offset);
                if (favl > avl) favl = avl;
                vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], favl);
                vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], favl);
                vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], favl);
                vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], favl);
                vfloat32m4_t a_out = __riscv_vfadd_vv_f32m4(va, vb, favl);
                a_out = __riscv_vfmacc_vf_f32m4(a_out, 0.25f, vc, favl);
                vfloat32m4_t d_out = __riscv_vfmacc_vf_f32m4(a_out, 0.125f, vx, favl);
                __riscv_vse32_v_f32m4(&a[offset], a_out, favl);
                __riscv_vse32_v_f32m4(&d[offset], d_out, favl);
            }
            if (offset < DB3_PHASE_B_ELEMS) {
                size_t iavl = (size_t)(DB3_PHASE_B_ELEMS - offset);
                if (iavl > avl) iavl = avl;
                vint16m2_t x0 = __riscv_vle16_v_i16m2(&db3_src0[offset], iavl);
                vint16m2_t x1 = __riscv_vle16_v_i16m2(&db3_src1[offset], iavl);
                vint16m2_t xb = __riscv_vle16_v_i16m2(&db3_bias[offset], iavl);
                vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, iavl);
                vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, iavl);
                vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, iavl);
                vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, iavl);
                vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, iavl);
                vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, iavl);
                vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, iavl);
                vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, iavl);
                vint32m4_t out = __riscv_vadd_vv_i32m4(acc0, acc1, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc2, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc3, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc4, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc5, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc6, iavl);
                out = __riscv_vadd_vv_i32m4(out, acc7, iavl);
                __riscv_vse32_v_i32m4(&indx[offset], out, iavl);
            }
        }
#endif
    }
}
