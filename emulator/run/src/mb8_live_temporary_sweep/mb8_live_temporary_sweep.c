#include "common.h"
#include "dlmul_variant.h"
#include <stdint.h>
#include <riscv_vector.h>

#ifndef MB8_CLASS
#define MB8_CLASS 1
#endif

#ifndef MB8_LMUL_VARIANT
#define MB8_LMUL_VARIANT DLMUL_LMUL_M1
#endif

#ifndef MB8_K
#define MB8_K 4
#endif

#ifndef MB8_TOTAL_ELEMS
#define MB8_TOTAL_ELEMS 64
#endif

#ifndef MB8_OUTER_ITERS
#define MB8_OUTER_ITERS 24
#endif

#if MB8_CLASS == 3
static int16_t mb8_src0[LEN_1D];
static int16_t mb8_src1[LEN_1D];
#endif

#if MB8_CLASS == 3
#if MB8_LMUL_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16mf2(avl);
    vint16mf2_t x = __riscv_vle16_v_i16mf2(&mb8_src0[offset], vl);
    vint16mf2_t y = __riscv_vle16_v_i16mf2(&mb8_src1[offset], vl);
    vint32m1_t t0 = __riscv_vwadd_vv_i32m1(x, y, vl);
    vint32m1_t t1 = __riscv_vwmul_vv_i32m1(x, y, vl);
    vint32m1_t out = __riscv_vadd_vv_i32m1(t0, t1, vl);
#if MB8_K >= 4
    vint32m1_t t2 = __riscv_vwadd_vv_i32m1(y, x, vl);
    vint32m1_t t3 = __riscv_vwmul_vv_i32m1(y, x, vl);
    out = __riscv_vadd_vv_i32m1(out, t2, vl);
    out = __riscv_vadd_vv_i32m1(out, t3, vl);
#endif
#if MB8_K >= 8
    vint32m1_t t4 = __riscv_vwadd_vv_i32m1(x, x, vl);
    vint32m1_t t5 = __riscv_vwadd_vv_i32m1(y, y, vl);
    vint32m1_t t6 = __riscv_vwmul_vv_i32m1(x, x, vl);
    vint32m1_t t7 = __riscv_vwmul_vv_i32m1(y, y, vl);
    out = __riscv_vadd_vv_i32m1(out, t4, vl);
    out = __riscv_vadd_vv_i32m1(out, t5, vl);
    out = __riscv_vadd_vv_i32m1(out, t6, vl);
    out = __riscv_vadd_vv_i32m1(out, t7, vl);
#endif
#if MB8_K >= 12
    vint32m1_t t8 = __riscv_vwadd_vv_i32m1(x, y, vl);
    vint32m1_t t9 = __riscv_vwmul_vv_i32m1(x, y, vl);
    vint32m1_t t10 = __riscv_vwadd_vv_i32m1(y, x, vl);
    vint32m1_t t11 = __riscv_vwmul_vv_i32m1(y, x, vl);
    out = __riscv_vadd_vv_i32m1(out, t8, vl);
    out = __riscv_vadd_vv_i32m1(out, t9, vl);
    out = __riscv_vadd_vv_i32m1(out, t10, vl);
    out = __riscv_vadd_vv_i32m1(out, t11, vl);
#endif
    __riscv_vse32_v_i32m1(&indx[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m1(avl);
    vint16m1_t x = __riscv_vle16_v_i16m1(&mb8_src0[offset], vl);
    vint16m1_t y = __riscv_vle16_v_i16m1(&mb8_src1[offset], vl);
    vint32m2_t t0 = __riscv_vwadd_vv_i32m2(x, y, vl);
    vint32m2_t t1 = __riscv_vwmul_vv_i32m2(x, y, vl);
    vint32m2_t out = __riscv_vadd_vv_i32m2(t0, t1, vl);
#if MB8_K >= 4
    vint32m2_t t2 = __riscv_vwadd_vv_i32m2(y, x, vl);
    vint32m2_t t3 = __riscv_vwmul_vv_i32m2(y, x, vl);
    out = __riscv_vadd_vv_i32m2(out, t2, vl);
    out = __riscv_vadd_vv_i32m2(out, t3, vl);
#endif
#if MB8_K >= 8
    vint32m2_t t4 = __riscv_vwadd_vv_i32m2(x, x, vl);
    vint32m2_t t5 = __riscv_vwadd_vv_i32m2(y, y, vl);
    vint32m2_t t6 = __riscv_vwmul_vv_i32m2(x, x, vl);
    vint32m2_t t7 = __riscv_vwmul_vv_i32m2(y, y, vl);
    out = __riscv_vadd_vv_i32m2(out, t4, vl);
    out = __riscv_vadd_vv_i32m2(out, t5, vl);
    out = __riscv_vadd_vv_i32m2(out, t6, vl);
    out = __riscv_vadd_vv_i32m2(out, t7, vl);
#endif
#if MB8_K >= 12
    vint32m2_t t8 = __riscv_vwadd_vv_i32m2(x, y, vl);
    vint32m2_t t9 = __riscv_vwmul_vv_i32m2(x, y, vl);
    vint32m2_t t10 = __riscv_vwadd_vv_i32m2(y, x, vl);
    vint32m2_t t11 = __riscv_vwmul_vv_i32m2(y, x, vl);
    out = __riscv_vadd_vv_i32m2(out, t8, vl);
    out = __riscv_vadd_vv_i32m2(out, t9, vl);
    out = __riscv_vadd_vv_i32m2(out, t10, vl);
    out = __riscv_vadd_vv_i32m2(out, t11, vl);
#endif
    __riscv_vse32_v_i32m2(&indx[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m2(avl);
    vint16m2_t x = __riscv_vle16_v_i16m2(&mb8_src0[offset], vl);
    vint16m2_t y = __riscv_vle16_v_i16m2(&mb8_src1[offset], vl);
    vint32m4_t t0 = __riscv_vwadd_vv_i32m4(x, y, vl);
    vint32m4_t t1 = __riscv_vwmul_vv_i32m4(x, y, vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(t0, t1, vl);
#if MB8_K >= 4
    vint32m4_t t2 = __riscv_vwadd_vv_i32m4(y, x, vl);
    vint32m4_t t3 = __riscv_vwmul_vv_i32m4(y, x, vl);
    out = __riscv_vadd_vv_i32m4(out, t2, vl);
    out = __riscv_vadd_vv_i32m4(out, t3, vl);
#endif
#if MB8_K >= 8
    vint32m4_t t4 = __riscv_vwadd_vv_i32m4(x, x, vl);
    vint32m4_t t5 = __riscv_vwadd_vv_i32m4(y, y, vl);
    vint32m4_t t6 = __riscv_vwmul_vv_i32m4(x, x, vl);
    vint32m4_t t7 = __riscv_vwmul_vv_i32m4(y, y, vl);
    out = __riscv_vadd_vv_i32m4(out, t4, vl);
    out = __riscv_vadd_vv_i32m4(out, t5, vl);
    out = __riscv_vadd_vv_i32m4(out, t6, vl);
    out = __riscv_vadd_vv_i32m4(out, t7, vl);
#endif
#if MB8_K >= 12
    vint32m4_t t8 = __riscv_vwadd_vv_i32m4(x, y, vl);
    vint32m4_t t9 = __riscv_vwmul_vv_i32m4(x, y, vl);
    vint32m4_t t10 = __riscv_vwadd_vv_i32m4(y, x, vl);
    vint32m4_t t11 = __riscv_vwmul_vv_i32m4(y, x, vl);
    out = __riscv_vadd_vv_i32m4(out, t8, vl);
    out = __riscv_vadd_vv_i32m4(out, t9, vl);
    out = __riscv_vadd_vv_i32m4(out, t10, vl);
    out = __riscv_vadd_vv_i32m4(out, t11, vl);
#endif
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&mb8_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&mb8_src1[offset], vl);
    vint32m8_t t0 = __riscv_vwadd_vv_i32m8(x, y, vl);
    vint32m8_t t1 = __riscv_vwmul_vv_i32m8(x, y, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(t0, t1, vl);
#if MB8_K >= 4
    vint32m8_t t2 = __riscv_vwadd_vv_i32m8(y, x, vl);
    vint32m8_t t3 = __riscv_vwmul_vv_i32m8(y, x, vl);
    out = __riscv_vadd_vv_i32m8(out, t2, vl);
    out = __riscv_vadd_vv_i32m8(out, t3, vl);
#endif
#if MB8_K >= 8
    vint32m8_t t4 = __riscv_vwadd_vv_i32m8(x, x, vl);
    vint32m8_t t5 = __riscv_vwadd_vv_i32m8(y, y, vl);
    vint32m8_t t6 = __riscv_vwmul_vv_i32m8(x, x, vl);
    vint32m8_t t7 = __riscv_vwmul_vv_i32m8(y, y, vl);
    out = __riscv_vadd_vv_i32m8(out, t4, vl);
    out = __riscv_vadd_vv_i32m8(out, t5, vl);
    out = __riscv_vadd_vv_i32m8(out, t6, vl);
    out = __riscv_vadd_vv_i32m8(out, t7, vl);
#endif
#if MB8_K >= 12
    vint32m8_t t8 = __riscv_vwadd_vv_i32m8(x, y, vl);
    vint32m8_t t9 = __riscv_vwmul_vv_i32m8(x, y, vl);
    vint32m8_t t10 = __riscv_vwadd_vv_i32m8(y, x, vl);
    vint32m8_t t11 = __riscv_vwmul_vv_i32m8(y, x, vl);
    out = __riscv_vadd_vv_i32m8(out, t8, vl);
    out = __riscv_vadd_vv_i32m8(out, t9, vl);
    out = __riscv_vadd_vv_i32m8(out, t10, vl);
    out = __riscv_vadd_vv_i32m8(out, t11, vl);
#endif
    __riscv_vse32_v_i32m8(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB8_LMUL_VARIANT"
#endif
#else
#if MB8_LMUL_VARIANT == DLMUL_LMUL_MF2
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32mf2(avl);
    vfloat32mf2_t t0 = __riscv_vle32_v_f32mf2(&a[offset], vl);
    vfloat32mf2_t t1 = __riscv_vle32_v_f32mf2(&b[offset], vl);
    vfloat32mf2_t out = __riscv_vfadd_vv_f32mf2(t0, t1, vl);
#if MB8_K >= 4
    vfloat32mf2_t t2 = __riscv_vle32_v_f32mf2(&c[offset], vl);
    vfloat32mf2_t t3 = __riscv_vle32_v_f32mf2(&d[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32mf2(out, t2, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t3, vl);
#else
    out = __riscv_vfmacc_vv_f32mf2(out, t2, t3, vl);
#endif
#endif
#if MB8_K >= 8
    vfloat32mf2_t t4 = __riscv_vle32_v_f32mf2(&e[offset], vl);
    vfloat32mf2_t t5 = __riscv_vle32_v_f32mf2(&x[offset], vl);
    vfloat32mf2_t t6 = __riscv_vle32_v_f32mf2(&aa[0][offset], vl);
    vfloat32mf2_t t7 = __riscv_vle32_v_f32mf2(&bb[0][offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32mf2(out, t4, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t5, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t6, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t7, vl);
#else
    out = __riscv_vfmacc_vv_f32mf2(out, t4, t5, vl);
    out = __riscv_vfmacc_vv_f32mf2(out, t6, t7, vl);
#endif
#endif
#if MB8_K >= 12
    vfloat32mf2_t t8 = __riscv_vle32_v_f32mf2(&cc[0][offset], vl);
    vfloat32mf2_t t9 = __riscv_vle32_v_f32mf2(&tt[0][offset], vl);
    vfloat32mf2_t t10 = __riscv_vle32_v_f32mf2(&flat_2d_array[offset], vl);
    vfloat32mf2_t t11 = __riscv_vle32_v_f32mf2(&a[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32mf2(out, t8, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t9, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t10, vl);
    out = __riscv_vfadd_vv_f32mf2(out, t11, vl);
#else
    out = __riscv_vfmacc_vv_f32mf2(out, t8, t9, vl);
    out = __riscv_vfmacc_vv_f32mf2(out, t10, t11, vl);
#endif
#endif
    __riscv_vse32_v_f32mf2(&a[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t t0 = __riscv_vle32_v_f32m1(&a[offset], vl);
    vfloat32m1_t t1 = __riscv_vle32_v_f32m1(&b[offset], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(t0, t1, vl);
#if MB8_K >= 4
    vfloat32m1_t t2 = __riscv_vle32_v_f32m1(&c[offset], vl);
    vfloat32m1_t t3 = __riscv_vle32_v_f32m1(&d[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m1(out, t2, vl);
    out = __riscv_vfadd_vv_f32m1(out, t3, vl);
#else
    out = __riscv_vfmacc_vv_f32m1(out, t2, t3, vl);
#endif
#endif
#if MB8_K >= 8
    vfloat32m1_t t4 = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t t5 = __riscv_vle32_v_f32m1(&x[offset], vl);
    vfloat32m1_t t6 = __riscv_vle32_v_f32m1(&aa[0][offset], vl);
    vfloat32m1_t t7 = __riscv_vle32_v_f32m1(&bb[0][offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m1(out, t4, vl);
    out = __riscv_vfadd_vv_f32m1(out, t5, vl);
    out = __riscv_vfadd_vv_f32m1(out, t6, vl);
    out = __riscv_vfadd_vv_f32m1(out, t7, vl);
#else
    out = __riscv_vfmacc_vv_f32m1(out, t4, t5, vl);
    out = __riscv_vfmacc_vv_f32m1(out, t6, t7, vl);
#endif
#endif
#if MB8_K >= 12
    vfloat32m1_t t8 = __riscv_vle32_v_f32m1(&cc[0][offset], vl);
    vfloat32m1_t t9 = __riscv_vle32_v_f32m1(&tt[0][offset], vl);
    vfloat32m1_t t10 = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t t11 = __riscv_vle32_v_f32m1(&a[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m1(out, t8, vl);
    out = __riscv_vfadd_vv_f32m1(out, t9, vl);
    out = __riscv_vfadd_vv_f32m1(out, t10, vl);
    out = __riscv_vfadd_vv_f32m1(out, t11, vl);
#else
    out = __riscv_vfmacc_vv_f32m1(out, t8, t9, vl);
    out = __riscv_vfmacc_vv_f32m1(out, t10, t11, vl);
#endif
#endif
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t t0 = __riscv_vle32_v_f32m2(&a[offset], vl);
    vfloat32m2_t t1 = __riscv_vle32_v_f32m2(&b[offset], vl);
    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(t0, t1, vl);
#if MB8_K >= 4
    vfloat32m2_t t2 = __riscv_vle32_v_f32m2(&c[offset], vl);
    vfloat32m2_t t3 = __riscv_vle32_v_f32m2(&d[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m2(out, t2, vl);
    out = __riscv_vfadd_vv_f32m2(out, t3, vl);
#else
    out = __riscv_vfmacc_vv_f32m2(out, t2, t3, vl);
#endif
#endif
#if MB8_K >= 8
    vfloat32m2_t t4 = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t t5 = __riscv_vle32_v_f32m2(&x[offset], vl);
    vfloat32m2_t t6 = __riscv_vle32_v_f32m2(&aa[0][offset], vl);
    vfloat32m2_t t7 = __riscv_vle32_v_f32m2(&bb[0][offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m2(out, t4, vl);
    out = __riscv_vfadd_vv_f32m2(out, t5, vl);
    out = __riscv_vfadd_vv_f32m2(out, t6, vl);
    out = __riscv_vfadd_vv_f32m2(out, t7, vl);
#else
    out = __riscv_vfmacc_vv_f32m2(out, t4, t5, vl);
    out = __riscv_vfmacc_vv_f32m2(out, t6, t7, vl);
#endif
#endif
#if MB8_K >= 12
    vfloat32m2_t t8 = __riscv_vle32_v_f32m2(&cc[0][offset], vl);
    vfloat32m2_t t9 = __riscv_vle32_v_f32m2(&tt[0][offset], vl);
    vfloat32m2_t t10 = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t t11 = __riscv_vle32_v_f32m2(&a[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m2(out, t8, vl);
    out = __riscv_vfadd_vv_f32m2(out, t9, vl);
    out = __riscv_vfadd_vv_f32m2(out, t10, vl);
    out = __riscv_vfadd_vv_f32m2(out, t11, vl);
#else
    out = __riscv_vfmacc_vv_f32m2(out, t8, t9, vl);
    out = __riscv_vfmacc_vv_f32m2(out, t10, t11, vl);
#endif
#endif
    __riscv_vse32_v_f32m2(&a[offset], out, vl);
    return vl;
}
#elif MB8_LMUL_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t mb8_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t t0 = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t t1 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(t0, t1, vl);
#if MB8_K >= 4
    vfloat32m4_t t2 = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t t3 = __riscv_vle32_v_f32m4(&d[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m4(out, t2, vl);
    out = __riscv_vfadd_vv_f32m4(out, t3, vl);
#else
    out = __riscv_vfmacc_vv_f32m4(out, t2, t3, vl);
#endif
#endif
#if MB8_K >= 8
    vfloat32m4_t t4 = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t t5 = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t t6 = __riscv_vle32_v_f32m4(&aa[0][offset], vl);
    vfloat32m4_t t7 = __riscv_vle32_v_f32m4(&bb[0][offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m4(out, t4, vl);
    out = __riscv_vfadd_vv_f32m4(out, t5, vl);
    out = __riscv_vfadd_vv_f32m4(out, t6, vl);
    out = __riscv_vfadd_vv_f32m4(out, t7, vl);
#else
    out = __riscv_vfmacc_vv_f32m4(out, t4, t5, vl);
    out = __riscv_vfmacc_vv_f32m4(out, t6, t7, vl);
#endif
#endif
#if MB8_K >= 12
    vfloat32m4_t t8 = __riscv_vle32_v_f32m4(&cc[0][offset], vl);
    vfloat32m4_t t9 = __riscv_vle32_v_f32m4(&tt[0][offset], vl);
    vfloat32m4_t t10 = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t t11 = __riscv_vle32_v_f32m4(&a[offset], vl);
#if MB8_CLASS == 1
    out = __riscv_vfadd_vv_f32m4(out, t8, vl);
    out = __riscv_vfadd_vv_f32m4(out, t9, vl);
    out = __riscv_vfadd_vv_f32m4(out, t10, vl);
    out = __riscv_vfadd_vv_f32m4(out, t11, vl);
#else
    out = __riscv_vfmacc_vv_f32m4(out, t8, t9, vl);
    out = __riscv_vfmacc_vv_f32m4(out, t10, t11, vl);
#endif
#endif
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported MB8_LMUL_VARIANT"
#endif
#endif

void kernel(void) {
#if MB8_CLASS == 3
    for (int i = 0; i < MB8_TOTAL_ELEMS; ++i) {
        mb8_src0[i] = (int16_t)((i % 9) + 1);
        mb8_src1[i] = (int16_t)((i % 7) + 3);
    }
#endif
    for (int iter = 0; iter < MB8_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = MB8_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = mb8_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
