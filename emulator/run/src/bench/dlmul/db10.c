#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#define DB10_TOTAL_ELEMS 224
#define DB10_OUTER_ITERS 32

#define DB10_STREAM_PHASE(lmul, src0, src1, dst) do { \
    int offset = 0; \
    int remaining = DB10_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&(src0)[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&(src1)[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.125f, va, vl); \
        DLB_VSE32(lmul)(&(dst)[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB10_RUN(a_lmul, b_lmul, c_lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB10_OUTER_ITERS; ++iter) { \
        DB10_STREAM_PHASE(a_lmul, a, b, a); \
        DB10_STREAM_PHASE(b_lmul, c, d, b); \
        DB10_STREAM_PHASE(c_lmul, e, x, c); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB10_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB10_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB10_RUN(m8, m8, m8);
#else
    DB10_RUN(m8, m2, m8);
#endif
}
