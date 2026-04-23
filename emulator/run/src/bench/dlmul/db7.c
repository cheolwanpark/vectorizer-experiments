#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M4
#endif

#define DB7_TOTAL_ELEMS 128
#define DB7_OUTER_ITERS 36

#define DB7_STREAM_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB7_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.1875f, vc, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB7_FIR_BANK(lmul) do { \
    int offset = 0; \
    int remaining = DB7_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) s0 = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) s1 = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) s2 = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) s3 = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) s4 = DLB_VLE32(lmul)(&e[offset], vl); \
        DLB_F32_T(lmul) s5 = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) s6 = DLB_VLE32(lmul)(&flat_2d_array[offset], vl); \
        DLB_F32_T(lmul) s7 = DLB_VLE32(lmul)(&flat_2d_array[DB7_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) s8 = DLB_VLE32(lmul)(&flat_2d_array[2 * DB7_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) s9 = DLB_VLE32(lmul)(&flat_2d_array[3 * DB7_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) s10 = DLB_VLE32(lmul)(&flat_2d_array[4 * DB7_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) s11 = DLB_VLE32(lmul)(&flat_2d_array[5 * DB7_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) acc0 = DLB_VFMUL(lmul)(s0, s1, vl); \
        DLB_F32_T(lmul) acc1 = DLB_VFMUL(lmul)(s2, s3, vl); \
        DLB_F32_T(lmul) acc2 = DLB_VFMUL(lmul)(s4, s5, vl); \
        DLB_F32_T(lmul) acc3 = DLB_VFMUL(lmul)(s6, s7, vl); \
        acc0 = DLB_VFMACC_VV(lmul)(acc0, s8, s9, vl); \
        acc1 = DLB_VFMACC_VV(lmul)(acc1, s10, s11, vl); \
        acc2 = DLB_VFMACC_VV(lmul)(acc2, s0, s3, vl); \
        acc3 = DLB_VFMACC_VV(lmul)(acc3, s2, s5, vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(acc0, acc1, vl); \
        out = DLB_VFADD(lmul)(out, acc2, vl); \
        out = DLB_VFADD(lmul)(out, acc3, vl); \
        DLB_VSE32(lmul)(&b[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB7_EPILOGUE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB7_TOTAL_ELEMS; \
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

#define DB7_RUN(a_lmul, b_lmul, c_lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB7_OUTER_ITERS; ++iter) { \
        DB7_STREAM_PHASE(a_lmul); \
        DB7_FIR_BANK(b_lmul); \
        DB7_EPILOGUE_PHASE(c_lmul); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB7_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB7_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB7_RUN(m8, m8, m8);
#else
    DB7_RUN(m8, m2, m4);
#endif
}
