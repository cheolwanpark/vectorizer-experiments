#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#ifndef DB3_PHASE_B_ELEMS
#define DB3_PHASE_B_ELEMS 96
#endif

#define DB3_WIDE_ELEMS 128
#define DB3_OUTER_ITERS 32

static int16_t db3_src0[LEN_1D];
static int16_t db3_src1[LEN_1D];
static int16_t db3_bias[LEN_1D];
static int32_t db3_acc[LEN_1D];

static void db3_init(void) {
    dlb_init_real_inputs();
    dlb_init_int16_triplet(db3_src0, db3_src1, db3_bias, DB3_PHASE_B_ELEMS);
}

#define DB3_WIDE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB3_WIDE_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.25f, vc, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB3_WIDEN_PHASE(src_lmul, dst_lmul) do { \
    int offset = 0; \
    int remaining = DB3_PHASE_B_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E16(src_lmul)((size_t)remaining); \
        DLB_I16_T(src_lmul) x0 = DLB_VLE16(src_lmul)(&db3_src0[offset], vl); \
        DLB_I16_T(src_lmul) x1 = DLB_VLE16(src_lmul)(&db3_src1[offset], vl); \
        DLB_I16_T(src_lmul) xb = DLB_VLE16(src_lmul)(&db3_bias[offset], vl); \
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
        DLB_VSE32_I(dst_lmul)(&db3_acc[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB3_EPILOGUE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB3_WIDE_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vx = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(va, 0.125f, vx, vl); \
        DLB_VSE32(lmul)(&d[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB3_RUN_FIXED(src_lmul, dst_lmul) do { \
    db3_init(); \
    for (int iter = 0; iter < DB3_OUTER_ITERS; ++iter) { \
        DB3_WIDE_PHASE(src_lmul); \
        DB3_WIDEN_PHASE(src_lmul, dst_lmul); \
        DB3_EPILOGUE_PHASE(src_lmul); \
    } \
} while (0)

static void run_dyn_m4_m2_m4(void) {
    db3_init();
    for (int iter = 0; iter < DB3_OUTER_ITERS; ++iter) {
        DB3_WIDE_PHASE(m4);
        DB3_WIDEN_PHASE(m2, m4);
        DB3_EPILOGUE_PHASE(m4);
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB3_RUN_FIXED(m2, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB3_RUN_FIXED(m4, m8);
#else
    run_dyn_m4_m2_m4();
#endif
}
