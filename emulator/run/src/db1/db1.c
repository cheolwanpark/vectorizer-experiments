#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB1_TOTAL_ELEMS 192
#define DB1_OUTER_ITERS 32

static int16_t db1_src0[LEN_1D];
static int16_t db1_src1[LEN_1D];
static int16_t db1_bias[LEN_1D];

void kernel(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db1_src0, db1_src1, db1_bias, DB1_TOTAL_ELEMS);

    for (int iter = 0; iter < DB1_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t ve = __riscv_vle32_v_f32m1(&e[offset], avl);
            vfloat32m1_t vx = __riscv_vle32_v_f32m1(&x[offset], avl);
            vfloat32m1_t t0 = __riscv_vfadd_vv_f32m1(va, vb, avl);
            vfloat32m1_t t1 = __riscv_vfmul_vv_f32m1(vc, vd, avl);
            vfloat32m1_t a_out = __riscv_vfmacc_vf_f32m1(t0, 0.25f, t1, avl);
            vfloat32m1_t d_out = __riscv_vfadd_vv_f32m1(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m1(d_out, 0.125f, vx, avl);

            vint16m1_t x0 = __riscv_vle16_v_i16m1(&db1_src0[offset], avl);
            vint16m1_t x1 = __riscv_vle16_v_i16m1(&db1_src1[offset], avl);
            vint16m1_t xb = __riscv_vle16_v_i16m1(&db1_bias[offset], avl);
            vint32m2_t acc0 = __riscv_vwadd_vv_i32m2(x0, x1, avl);
            vint32m2_t acc1 = __riscv_vwmul_vv_i32m2(x0, x1, avl);
            vint32m2_t acc2 = __riscv_vwadd_vv_i32m2(x1, xb, avl);
            vint32m2_t acc3 = __riscv_vwmul_vv_i32m2(x1, xb, avl);
            vint32m2_t acc4 = __riscv_vwadd_vv_i32m2(x0, xb, avl);
            vint32m2_t acc5 = __riscv_vwmul_vv_i32m2(x0, xb, avl);
            vint32m2_t acc6 = __riscv_vwadd_vv_i32m2(xb, x1, avl);
            vint32m2_t acc7 = __riscv_vwmul_vv_i32m2(xb, x0, avl);
            vint32m2_t i_out = __riscv_vadd_vv_i32m2(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m2(i_out, acc7, avl);

            __riscv_vse32_v_f32m1(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m1(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m2(&indx[offset], i_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], avl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], avl);
            vfloat32m2_t t0 = __riscv_vfadd_vv_f32m2(va, vb, avl);
            vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(vc, vd, avl);
            vfloat32m2_t a_out = __riscv_vfmacc_vf_f32m2(t0, 0.25f, t1, avl);
            vfloat32m2_t d_out = __riscv_vfadd_vv_f32m2(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m2(d_out, 0.125f, vx, avl);

            vint16m2_t x0 = __riscv_vle16_v_i16m2(&db1_src0[offset], avl);
            vint16m2_t x1 = __riscv_vle16_v_i16m2(&db1_src1[offset], avl);
            vint16m2_t xb = __riscv_vle16_v_i16m2(&db1_bias[offset], avl);
            vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, avl);
            vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, avl);
            vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, avl);
            vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, avl);
            vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, avl);
            vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, avl);
            vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, avl);
            vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, avl);
            vint32m4_t i_out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc7, avl);

            __riscv_vse32_v_f32m2(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m2(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], i_out, avl);
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t t0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t t1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t a_out = __riscv_vfmacc_vf_f32m4(t0, 0.25f, t1, avl);
            vfloat32m4_t d_out = __riscv_vfadd_vv_f32m4(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m4(d_out, 0.125f, vx, avl);

            vint16m4_t x0 = __riscv_vle16_v_i16m4(&db1_src0[offset], avl);
            vint16m4_t x1 = __riscv_vle16_v_i16m4(&db1_src1[offset], avl);
            vint16m4_t xb = __riscv_vle16_v_i16m4(&db1_bias[offset], avl);
            vint32m8_t acc0 = __riscv_vwadd_vv_i32m8(x0, x1, avl);
            vint32m8_t acc1 = __riscv_vwmul_vv_i32m8(x0, x1, avl);
            vint32m8_t acc2 = __riscv_vwadd_vv_i32m8(x1, xb, avl);
            vint32m8_t acc3 = __riscv_vwmul_vv_i32m8(x1, xb, avl);
            vint32m8_t acc4 = __riscv_vwadd_vv_i32m8(x0, xb, avl);
            vint32m8_t acc5 = __riscv_vwmul_vv_i32m8(x0, xb, avl);
            vint32m8_t acc6 = __riscv_vwadd_vv_i32m8(xb, x1, avl);
            vint32m8_t acc7 = __riscv_vwmul_vv_i32m8(xb, x0, avl);
            vint32m8_t i_out = __riscv_vadd_vv_i32m8(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m8(i_out, acc7, avl);

            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m8(&indx[offset], i_out, avl);
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)DB1_TOTAL_ELEMS);
        for (int offset = 0; offset < DB1_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(DB1_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t t0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t t1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t a_out = __riscv_vfmacc_vf_f32m4(t0, 0.25f, t1, avl);
            vfloat32m4_t d_out = __riscv_vfadd_vv_f32m4(a_out, ve, avl);
            d_out = __riscv_vfmacc_vf_f32m4(d_out, 0.125f, vx, avl);

            vint16m2_t x0 = __riscv_vle16_v_i16m2(&db1_src0[offset], avl);
            vint16m2_t x1 = __riscv_vle16_v_i16m2(&db1_src1[offset], avl);
            vint16m2_t xb = __riscv_vle16_v_i16m2(&db1_bias[offset], avl);
            vint32m4_t acc0 = __riscv_vwadd_vv_i32m4(x0, x1, avl);
            vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(x0, x1, avl);
            vint32m4_t acc2 = __riscv_vwadd_vv_i32m4(x1, xb, avl);
            vint32m4_t acc3 = __riscv_vwmul_vv_i32m4(x1, xb, avl);
            vint32m4_t acc4 = __riscv_vwadd_vv_i32m4(x0, xb, avl);
            vint32m4_t acc5 = __riscv_vwmul_vv_i32m4(x0, xb, avl);
            vint32m4_t acc6 = __riscv_vwadd_vv_i32m4(xb, x1, avl);
            vint32m4_t acc7 = __riscv_vwmul_vv_i32m4(xb, x0, avl);
            vint32m4_t i_out = __riscv_vadd_vv_i32m4(acc0, acc1, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc2, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc3, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc4, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc5, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc6, avl);
            i_out = __riscv_vadd_vv_i32m4(i_out, acc7, avl);

            __riscv_vsetvl_e32m4(avl);
            __riscv_vse32_v_f32m4(&a[offset], a_out, avl);
            __riscv_vse32_v_f32m4(&d[offset], d_out, avl);
            __riscv_vse32_v_i32m4(&indx[offset], i_out, avl);
        }
#endif
    }
}
