#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#define DB5_TOTAL_ELEMS 192
#define DB5_OUTER_ITERS 36

#define DB5_STREAM_PHASE(lmul, dst_array) do { \
    int offset = 0; \
    int remaining = DB5_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.25f, vc, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.125f, vd, vl); \
        DLB_VSE32(lmul)(&(dst_array)[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB5_RUN(lmul_a, lmul_b, lmul_c) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB5_OUTER_ITERS; ++iter) { \
        DB5_STREAM_PHASE(lmul_a, a); \
        DB5_STREAM_PHASE(lmul_b, b); \
        DB5_STREAM_PHASE(lmul_c, c); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB5_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB5_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB5_RUN(m8, m8, m8);
#else
    DB5_RUN(m8, m2, m8);
#endif
}
