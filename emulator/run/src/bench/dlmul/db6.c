#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M2
#endif

#define DB6_TOTAL_ELEMS 192
#define DB6_OUTER_ITERS 32

static int16_t db6_lhs[LEN_1D];
static int16_t db6_rhs[LEN_1D];
static int16_t db6_zp[LEN_1D];
static int32_t db6_acc[LEN_1D];
static int32_t db6_bias[LEN_1D];
static int32_t db6_out[LEN_1D];

static void db6_init(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db6_lhs, db6_rhs, db6_zp, DB6_TOTAL_ELEMS);
    for (int i = 0; i < DB6_TOTAL_ELEMS; ++i) {
        db6_bias[i] = (int32_t)((i % 29) - 14);
    }
}

#define DB6_PREFETCH_SCALE(lmul) do { \
    int offset = 0; \
    int remaining = DB6_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.25f, vc, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.125f, vd, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB6_DOT_CORE(src_lmul, dst_lmul) do { \
    int offset = 0; \
    int remaining = DB6_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E16(src_lmul)((size_t)remaining); \
        DLB_I16_T(src_lmul) lhs = DLB_VLE16(src_lmul)(&db6_lhs[offset], vl); \
        DLB_I16_T(src_lmul) rhs = DLB_VLE16(src_lmul)(&db6_rhs[offset], vl); \
        DLB_I16_T(src_lmul) zp = DLB_VLE16(src_lmul)(&db6_zp[offset], vl); \
        DLB_I32_T(dst_lmul) acc0 = DLB_VWMUL_I32(dst_lmul)(lhs, rhs, vl); \
        DLB_I32_T(dst_lmul) acc1 = DLB_VWADD_I32(dst_lmul)(lhs, zp, vl); \
        DLB_I32_T(dst_lmul) acc2 = DLB_VWMUL_I32(dst_lmul)(rhs, zp, vl); \
        DLB_I32_T(dst_lmul) acc3 = DLB_VWADD_I32(dst_lmul)(rhs, lhs, vl); \
        DLB_I32_T(dst_lmul) acc4 = DLB_VWMUL_I32(dst_lmul)(lhs, lhs, vl); \
        DLB_I32_T(dst_lmul) acc5 = DLB_VWADD_I32(dst_lmul)(rhs, rhs, vl); \
        DLB_I32_T(dst_lmul) acc6 = DLB_VWMUL_I32(dst_lmul)(zp, lhs, vl); \
        DLB_I32_T(dst_lmul) acc7 = DLB_VWADD_I32(dst_lmul)(zp, rhs, vl); \
        DLB_I32_T(dst_lmul) out = DLB_VADD_I32(dst_lmul)(acc0, acc1, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc2, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc3, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc4, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc5, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc6, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc7, vl); \
        DLB_VSE32_I(dst_lmul)(&db6_acc[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB6_BIAS_STORE(lmul) do { \
    int offset = 0; \
    int remaining = DB6_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_I32_T(lmul) acc = DLB_VLE32_I(lmul)(&db6_acc[offset], vl); \
        DLB_I32_T(lmul) bias = DLB_VLE32_I(lmul)(&db6_bias[offset], vl); \
        DLB_I32_T(lmul) out = DLB_VADD_I32(lmul)(acc, bias, vl); \
        DLB_VSE32_I(lmul)(&db6_out[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB6_RUN_FIXED(src_lmul, dst_lmul) do { \
    db6_init(); \
    for (int iter = 0; iter < DB6_OUTER_ITERS; ++iter) { \
        DB6_PREFETCH_SCALE(src_lmul); \
        DB6_DOT_CORE(src_lmul, dst_lmul); \
        DB6_BIAS_STORE(src_lmul); \
    } \
} while (0)

static void run_dyn_m8_m2_m2(void) {
    db6_init();
    for (int iter = 0; iter < DB6_OUTER_ITERS; ++iter) {
        DB6_PREFETCH_SCALE(m8);
        DB6_DOT_CORE(m2, m4);
        DB6_BIAS_STORE(m2);
    }
}

static void run_dyn_m8_m2_m4(void) {
    db6_init();
    for (int iter = 0; iter < DB6_OUTER_ITERS; ++iter) {
        DB6_PREFETCH_SCALE(m8);
        DB6_DOT_CORE(m2, m4);
        DB6_BIAS_STORE(m4);
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    DB6_RUN_FIXED(m1, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB6_RUN_FIXED(m2, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB6_RUN_FIXED(m4, m8);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_DYN_M8_M2_M4
    run_dyn_m8_m2_m4();
#else
    run_dyn_m8_m2_m2();
#endif
}
