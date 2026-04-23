#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB4_TOTAL_ELEMS 192
#define DB4_OUTER_ITERS 30

static int16_t db4_lhs[LEN_1D];
static int16_t db4_rhs[LEN_1D];
static int16_t db4_zp[LEN_1D];
static int32_t db4_acc[LEN_1D];
static int32_t db4_bias[LEN_1D];
static int32_t db4_out[LEN_1D];

static void db4_init(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db4_lhs, db4_rhs, db4_zp, DB4_TOTAL_ELEMS);
    for (int i = 0; i < DB4_TOTAL_ELEMS; ++i) {
        db4_bias[i] = (int32_t)((i % 23) - 11);
    }
}

#define DB4_LOAD_SCALE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB4_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) scale = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) bias = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(scale, 0.5f, bias, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB4_DOT_CORE(src_lmul, dst_lmul) do { \
    int offset = 0; \
    int remaining = DB4_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E16(src_lmul)((size_t)remaining); \
        DLB_I16_T(src_lmul) lhs = DLB_VLE16(src_lmul)(&db4_lhs[offset], vl); \
        DLB_I16_T(src_lmul) rhs = DLB_VLE16(src_lmul)(&db4_rhs[offset], vl); \
        DLB_I16_T(src_lmul) zp = DLB_VLE16(src_lmul)(&db4_zp[offset], vl); \
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
        DLB_VSE32_I(dst_lmul)(&db4_acc[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB4_BIAS_EPILOGUE(lmul) do { \
    int offset = 0; \
    int remaining = DB4_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_I32_T(lmul) acc = DLB_VLE32_I(lmul)(&db4_acc[offset], vl); \
        DLB_I32_T(lmul) bias = DLB_VLE32_I(lmul)(&db4_bias[offset], vl); \
        DLB_I32_T(lmul) out = DLB_VADD_I32(lmul)(acc, bias, vl); \
        DLB_VSE32_I(lmul)(&db4_out[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB4_RUN_FIXED(src_lmul, dst_lmul) do { \
    db4_init(); \
    for (int iter = 0; iter < DB4_OUTER_ITERS; ++iter) { \
        DB4_LOAD_SCALE_PHASE(src_lmul); \
        DB4_DOT_CORE(src_lmul, dst_lmul); \
        DB4_BIAS_EPILOGUE(src_lmul); \
    } \
} while (0)

static void run_dyn_m4_m2_m4(void) {
    db4_init();
    for (int iter = 0; iter < DB4_OUTER_ITERS; ++iter) {
        DB4_LOAD_SCALE_PHASE(m4);
        DB4_DOT_CORE(m2, m4);
        DB4_BIAS_EPILOGUE(m4);
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    DB4_RUN_FIXED(m1, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB4_RUN_FIXED(m2, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB4_RUN_FIXED(m4, m8);
#else
    run_dyn_m4_m2_m4();
#endif
}
