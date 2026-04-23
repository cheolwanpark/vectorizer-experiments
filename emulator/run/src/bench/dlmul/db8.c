#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M8_M2_M8
#endif

#ifndef DB8_PRESSURE_REPEATS
#define DB8_PRESSURE_REPEATS 2
#endif

#define DB8_TOTAL_ELEMS 128
#define DB8_OUTER_ITERS 28

#define DB8_STREAM_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB8_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFADD(lmul)(va, vb, vl); \
        DLB_VSE32(lmul)(&a[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB8_PRESSURE_ONCE(lmul) do { \
    int offset = 0; \
    int remaining = DB8_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) t0 = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) t1 = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) t2 = DLB_VLE32(lmul)(&c[offset], vl); \
        DLB_F32_T(lmul) t3 = DLB_VLE32(lmul)(&d[offset], vl); \
        DLB_F32_T(lmul) t4 = DLB_VLE32(lmul)(&e[offset], vl); \
        DLB_F32_T(lmul) t5 = DLB_VLE32(lmul)(&x[offset], vl); \
        DLB_F32_T(lmul) t6 = DLB_VLE32(lmul)(&flat_2d_array[offset], vl); \
        DLB_F32_T(lmul) t7 = DLB_VLE32(lmul)(&flat_2d_array[DB8_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t8 = DLB_VLE32(lmul)(&flat_2d_array[2 * DB8_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t9 = DLB_VLE32(lmul)(&flat_2d_array[3 * DB8_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t10 = DLB_VLE32(lmul)(&flat_2d_array[4 * DB8_TOTAL_ELEMS + offset], vl); \
        DLB_F32_T(lmul) t11 = DLB_VLE32(lmul)(&flat_2d_array[5 * DB8_TOTAL_ELEMS + offset], vl); \
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

#define DB8_PRESSURE_PHASE(lmul) do { \
    for (int repeat = 0; repeat < DB8_PRESSURE_REPEATS; ++repeat) { \
        DB8_PRESSURE_ONCE(lmul); \
    } \
} while (0)

#define DB8_EPILOGUE_PHASE(lmul) do { \
    int offset = 0; \
    int remaining = DB8_TOTAL_ELEMS; \
    while (remaining > 0) { \
        size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
        DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
        DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
        DLB_F32_T(lmul) out = DLB_VFMACC_VF(lmul)(va, 0.375f, vb, vl); \
        DLB_VSE32(lmul)(&d[offset], out, vl); \
        remaining -= (int)vl; \
        offset += (int)vl; \
    } \
} while (0)

#define DB8_RUN(a_lmul, b_lmul, c_lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < DB8_OUTER_ITERS; ++iter) { \
        DB8_STREAM_PHASE(a_lmul); \
        DB8_PRESSURE_PHASE(b_lmul); \
        DB8_EPILOGUE_PHASE(c_lmul); \
    } \
} while (0)

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    DB8_RUN(m2, m2, m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    DB8_RUN(m4, m4, m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M8
    DB8_RUN(m8, m8, m8);
#else
    DB8_RUN(m8, m2, m8);
#endif
}
