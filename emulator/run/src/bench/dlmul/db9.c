#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M4
#endif

#define DB9_TOTAL_ELEMS 128
#define DB9_OUTER_ITERS 34

#define DB9_LOAD_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB9_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) r = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) g = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) b0 = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) y = DLB_VFADD(lmul)(r, g, vl); \
        y = DLB_VFMACC_VF(lmul)(y, 0.5f, b0, vl); \
        DLB_VSE32(lmul)(&a[offset], y, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB9_GAMMA_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB9_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) y = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) u = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) v = DLB_VLE32(lmul)(&e[offset], vl); \
        DLB_F32_T(lmul) k0 = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) k1 = DLB_VLE32(lmul)(&flat_2d_array[offset], vl); \
        DLB_F32_T(lmul) k2 = DLB_VLE32(lmul)(&flat_2d_array[DB9_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) y2 = DLB_VFMUL(lmul)(y, y, vl); \
        DLB_F32_T(lmul) u2 = DLB_VFMUL(lmul)(u, u, vl); \
        DLB_F32_T(lmul) v2 = DLB_VFMUL(lmul)(v, v, vl); \
        DLB_F32_T(lmul) p0 = DLB_VFMACC_VV(lmul)(y, y2, k0, vl); \
        DLB_F32_T(lmul) p1 = DLB_VFMACC_VV(lmul)(u, u2, k1, vl); \
        DLB_F32_T(lmul) p2 = DLB_VFMACC_VV(lmul)(v, v2, k2, vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(p0, p1, vl); \
        out = DLB_VFADD(lmul)(out, p2, vl); \
        out = DLB_VFMACC_VF(lmul)(out, 0.125f, y2, vl); \
        DLB_VSE32(lmul)(&b[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB9_STORE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB9_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) ya = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) gb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(ya, 0.25f, gb, vl); \
        DLB_VSE32(lmul)(&c[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB9_RUN(a_lmul, b_lmul, c_lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB9_OUTER_ITERS; ++iter) { \
        DB9_LOAD_PHASE(a_lmul); \
        DB9_GAMMA_PHASE(b_lmul); \
        DB9_STORE_PHASE(c_lmul); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB9_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB9_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB9_RUN(m8, m8, m8);
#else
    DB9_RUN(m8, m2, m4);
#endif
}
