#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#define DB2_TOTAL_ELEMS 128
#define DB2_OUTER_ITERS 40

#define DB2_STREAM_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB2_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.375f, vc, vl); \
        out = DLB_VFMUL(lmul)(out, vd, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB2_FMA_ISLAND(lmul) do { \
    int offset = 0; \
    int remaining = DB2_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) t0 = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) t1 = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) t2 = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) t3 = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) t4 = DLB_VLE32(lmul)(&e[offset], vl); \
        DLB_F32_T(lmul) t5 = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) t6 = DLB_VLE32(lmul)(&flat_2d_array[offset], vl); \
        DLB_F32_T(lmul) t7 = DLB_VLE32(lmul)(&flat_2d_array[DB2_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t8 = DLB_VLE32(lmul)(&flat_2d_array[2 * DB2_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t9 = DLB_VLE32(lmul)(&flat_2d_array[3 * DB2_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t10 = DLB_VLE32(lmul)(&flat_2d_array[4 * DB2_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t11 = DLB_VLE32(lmul)(&flat_2d_array[5 * DB2_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(t0, t1, vl); \
        out = DLB_VFMACC_VV(lmul)(out, t2, t3, vl); \
        out = DLB_VFMACC_VV(lmul)(out, t4, t5, vl); \
        out = DLB_VFMACC_VV(lmul)(out, t6, t7, vl); \
        out = DLB_VFMACC_VV(lmul)(out, t8, t9, vl); \
        out = DLB_VFMACC_VV(lmul)(out, t10, t11, vl); \
        DLB_VSE32(lmul)(&b[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB2_EPILOGUE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB2_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(va, 0.5f, vb, vl); \
        DLB_VSE32(lmul)(&c[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB2_RUN(lmul_a, lmul_b, lmul_c) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB2_OUTER_ITERS; ++iter) { \
        DB2_STREAM_PHASE(lmul_a); \
        DB2_FMA_ISLAND(lmul_b); \
        DB2_EPILOGUE_PHASE(lmul_c); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB2_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB2_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB2_RUN(m8, m8, m8);
#else
    DB2_RUN(m8, m2, m8);
#endif
}
