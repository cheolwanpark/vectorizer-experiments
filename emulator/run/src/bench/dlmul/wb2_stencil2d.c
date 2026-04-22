#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#define WB2_INNER_COLS (LEN_2D - 2)

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase1_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t up = __riscv_vle32_v_f32m1(&aa[row - 1][col], vl);
    vfloat32m1_t mid = __riscv_vle32_v_f32m1(&aa[row][col], vl);
    vfloat32m1_t down = __riscv_vle32_v_f32m1(&aa[row + 1][col], vl);
    vfloat32m1_t partial = __riscv_vfadd_vv_f32m1(up, mid, vl);
    partial = __riscv_vfadd_vv_f32m1(partial, down, vl);
    __riscv_vse32_v_f32m1(&d[linear], partial, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase1_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t up = __riscv_vle32_v_f32m2(&aa[row - 1][col], vl);
    vfloat32m2_t mid = __riscv_vle32_v_f32m2(&aa[row][col], vl);
    vfloat32m2_t down = __riscv_vle32_v_f32m2(&aa[row + 1][col], vl);
    vfloat32m2_t partial = __riscv_vfadd_vv_f32m2(up, mid, vl);
    partial = __riscv_vfadd_vv_f32m2(partial, down, vl);
    __riscv_vse32_v_f32m2(&d[linear], partial, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase1_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t up = __riscv_vle32_v_f32m4(&aa[row - 1][col], vl);
    vfloat32m4_t mid = __riscv_vle32_v_f32m4(&aa[row][col], vl);
    vfloat32m4_t down = __riscv_vle32_v_f32m4(&aa[row + 1][col], vl);
    vfloat32m4_t partial = __riscv_vfadd_vv_f32m4(up, mid, vl);
    partial = __riscv_vfadd_vv_f32m4(partial, down, vl);
    __riscv_vse32_v_f32m4(&d[linear], partial, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase2_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t left = __riscv_vle32_v_f32m1(&aa[row][col - 1], vl);
    vfloat32m1_t right = __riscv_vle32_v_f32m1(&aa[row][col + 1], vl);
    vfloat32m1_t partial = __riscv_vle32_v_f32m1(&d[linear], vl);
    vfloat32m1_t center = __riscv_vle32_v_f32m1(&aa[row][col], vl);
    vfloat32m1_t out = __riscv_vfadd_vv_f32m1(left, right, vl);
    out = __riscv_vfadd_vv_f32m1(out, partial, vl);
    out = __riscv_vfmacc_vf_f32m1(out, 0.25f, center, vl);
    __riscv_vse32_v_f32m1(&flat_2d_array[linear], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase2_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t left = __riscv_vle32_v_f32m2(&aa[row][col - 1], vl);
    vfloat32m2_t right = __riscv_vle32_v_f32m2(&aa[row][col + 1], vl);
    vfloat32m2_t partial = __riscv_vle32_v_f32m2(&d[linear], vl);
    vfloat32m2_t center = __riscv_vle32_v_f32m2(&aa[row][col], vl);
    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(left, right, vl);
    out = __riscv_vfadd_vv_f32m2(out, partial, vl);
    out = __riscv_vfmacc_vf_f32m2(out, 0.25f, center, vl);
    __riscv_vse32_v_f32m2(&flat_2d_array[linear], out, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase2_step(int row, int col, int linear, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t left = __riscv_vle32_v_f32m4(&aa[row][col - 1], vl);
    vfloat32m4_t right = __riscv_vle32_v_f32m4(&aa[row][col + 1], vl);
    vfloat32m4_t partial = __riscv_vle32_v_f32m4(&d[linear], vl);
    vfloat32m4_t center = __riscv_vle32_v_f32m4(&aa[row][col], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(left, right, vl);
    out = __riscv_vfadd_vv_f32m4(out, partial, vl);
    out = __riscv_vfmacc_vf_f32m4(out, 0.25f, center, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[linear], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m1(avl);
    vfloat32m1_t acc = __riscv_vle32_v_f32m1(&flat_2d_array[offset], vl);
    vfloat32m1_t blend = __riscv_vle32_v_f32m1(&e[offset], vl);
    vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(acc, 0.125f, blend, vl);
    __riscv_vse32_v_f32m1(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m2(avl);
    vfloat32m2_t acc = __riscv_vle32_v_f32m2(&flat_2d_array[offset], vl);
    vfloat32m2_t blend = __riscv_vle32_v_f32m2(&e[offset], vl);
    vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(acc, 0.125f, blend, vl);
    __riscv_vse32_v_f32m2(&a[offset], out, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t acc = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t blend = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(acc, 0.125f, blend, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int row = 1;
        int linear = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0 && row < LEN_2D - 1) {
            int row_remaining = remaining < WB2_INNER_COLS ? remaining : WB2_INNER_COLS;
            int col = 1;
            while (row_remaining > 0) {
                size_t vl = wb2_phase1_step(row, col, linear, (size_t)row_remaining);
                row_remaining -= (int)vl;
                col += (int)vl;
                linear += (int)vl;
                remaining -= (int)vl;
            }
            row += 1;
        }

        row = 1;
        linear = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0 && row < LEN_2D - 1) {
            int row_remaining = remaining < WB2_INNER_COLS ? remaining : WB2_INNER_COLS;
            int col = 1;
            while (row_remaining > 0) {
                size_t vl = wb2_phase2_step(row, col, linear, (size_t)row_remaining);
                row_remaining -= (int)vl;
                col += (int)vl;
                linear += (int)vl;
                remaining -= (int)vl;
            }
            row += 1;
        }

        int offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb2_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
