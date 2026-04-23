#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#define DB1_TOTAL_ELEMS 192
#define DB1_OUTER_ITERS 32

static int16_t db1_src0[LEN_1D];
static int16_t db1_src1[LEN_1D];
static int16_t db1_bias[LEN_1D];
static int32_t db1_acc[LEN_1D];

static void db1_init(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db1_src0, db1_src1, db1_bias, DB1_TOTAL_ELEMS);
}

#define DB1_WIDE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB1_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) t0 = DLB_VFADD(lmul)(va, vb, vl); \
        DLB_F32_T(lmul) t1 = DLB_VFMUL(lmul)(vc, vd, vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(t0, 0.25f, t1, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB1_WIDEN_PHASE(src_lmul, dst_lmul) do { \
    int offset = 0; \
    int remaining = DB1_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E16(src_lmul)((size_t)remaining); \
        DLB_I16_T(src_lmul) x0 = DLB_VLE16(src_lmul)(&db1_src0[offset], vl); \
        DLB_I16_T(src_lmul) x1 = DLB_VLE16(src_lmul)(&db1_src1[offset], vl); \
        DLB_I16_T(src_lmul) xb = DLB_VLE16(src_lmul)(&db1_bias[offset], vl); \
        DLB_I32_T(dst_lmul) acc0 = DLB_VWADD_I32(dst_lmul)(x0, x1, vl); \
        DLB_I32_T(dst_lmul) acc1 = DLB_VWMUL_I32(dst_lmul)(x0, x1, vl); \
        DLB_I32_T(dst_lmul) acc2 = DLB_VWADD_I32(dst_lmul)(x1, xb, vl); \
        DLB_I32_T(dst_lmul) acc3 = DLB_VWMUL_I32(dst_lmul)(x1, xb, vl); \
        DLB_I32_T(dst_lmul) acc4 = DLB_VWADD_I32(dst_lmul)(x0, xb, vl); \
        DLB_I32_T(dst_lmul) acc5 = DLB_VWMUL_I32(dst_lmul)(x0, xb, vl); \
        DLB_I32_T(dst_lmul) acc6 = DLB_VWADD_I32(dst_lmul)(xb, x1, vl); \
        DLB_I32_T(dst_lmul) acc7 = DLB_VWMUL_I32(dst_lmul)(xb, x0, vl); \
        DLB_I32_T(dst_lmul) out = DLB_VADD_I32(dst_lmul)(acc0, acc1, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc2, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc3, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc4, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc5, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc6, vl); \
        out = DLB_VADD_I32(dst_lmul)(out, acc7, vl); \
        DLB_VSE32_I(dst_lmul)(&db1_acc[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB1_EPILOGUE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB1_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) ve = DLB_VLE32(lmul)(&e[offset], vl); \
        DLB_F32_T(lmul) vx = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, ve, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.125f, vx, vl); \
        DLB_VSE32(lmul)(&d[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

static void run_fixed_m1(void) {
    db1_init();
    for (int iter = 0; iter < DB1_OUTER_ITERS; ++iter) {
        DB1_WIDE_PHASE(m1);
        DB1_WIDEN_PHASE(m1, m2);
        DB1_EPILOGUE_PHASE(m1);
    }
}

static void run_fixed_m2(void) {
    db1_init();
    for (int iter = 0; iter < DB1_OUTER_ITERS; ++iter) {
        DB1_WIDE_PHASE(m2);
        DB1_WIDEN_PHASE(m2, m4);
        DB1_EPILOGUE_PHASE(m2);
    }
}

static void run_fixed_m4(void) {
    db1_init();
    for (int iter = 0; iter < DB1_OUTER_ITERS; ++iter) {
        DB1_WIDE_PHASE(m4);
        DB1_WIDEN_PHASE(m4, m8);
        DB1_EPILOGUE_PHASE(m4);
    }
}

static void run_dyn_m4_m2_m4(void) {
    db1_init();
    for (int iter = 0; iter < DB1_OUTER_ITERS; ++iter) {
        DB1_WIDE_PHASE(m4);
        DB1_WIDEN_PHASE(m2, m4);
        DB1_EPILOGUE_PHASE(m4);
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    run_fixed_m1();
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    run_fixed_m2();
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    run_fixed_m4();
#else
    run_dyn_m4_m2_m4();
#endif
}
