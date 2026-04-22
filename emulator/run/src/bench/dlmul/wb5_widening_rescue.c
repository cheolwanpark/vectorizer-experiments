#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];
static int32_t wb5_phase1[LEN_1D];
static int32_t wb5_phase2[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB5_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint32m2_t partial = __riscv_vwadd_vv_i32m2(x, y, vlc); \
        partial_big = __riscv_vset_v_i32m2_i32m8(partial_big, K, partial); \
    } \
} while (0)

    WB5_PHASE1_CHUNK_M1(0);
    WB5_PHASE1_CHUNK_M1(1);
    WB5_PHASE1_CHUNK_M1(2);
    WB5_PHASE1_CHUNK_M1(3);
#undef WB5_PHASE1_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB5_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint32m4_t partial = __riscv_vwadd_vv_i32m4(x, y, vlc); \
        partial_big = __riscv_vset_v_i32m4_i32m8(partial_big, K, partial); \
    } \
} while (0)

    WB5_PHASE1_CHUNK_M2(0);
    WB5_PHASE1_CHUNK_M2(1);
#undef WB5_PHASE1_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb5_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint32m8_t partial = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb5_phase1[offset], partial, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb5_src2[offset], vl);
    vint32m8_t seed_big = __riscv_vle32_v_i32m8(&wb5_phase1[offset], vl);
    vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB5_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint16m1_t z = __riscv_vget_v_i16m4_i16m1(z_big, K); \
        vint32m2_t seed = __riscv_vget_v_i32m8_i32m2(seed_big, K); \
        vint32m2_t t0 = __riscv_vwadd_vv_i32m2(x, y, vlc); \
        vint32m2_t t1 = __riscv_vwmul_vv_i32m2(x, y, vlc); \
        vint32m2_t t2 = __riscv_vwadd_vv_i32m2(y, z, vlc); \
        vint32m2_t t3 = __riscv_vwmul_vv_i32m2(y, z, vlc); \
        vint32m2_t t4 = __riscv_vwadd_vv_i32m2(x, z, vlc); \
        vint32m2_t t5 = __riscv_vwmul_vv_i32m2(x, z, vlc); \
        vint32m2_t t6 = __riscv_vwadd_vv_i32m2(x, x, vlc); \
        vint32m2_t t7 = __riscv_vwadd_vv_i32m2(y, y, vlc); \
        vint32m2_t t8 = __riscv_vwmul_vv_i32m2(z, z, vlc); \
        vint32m2_t t9 = __riscv_vwmul_vv_i32m2(y, x, vlc); \
        vint32m2_t t10 = __riscv_vwadd_vv_i32m2(z, x, vlc); \
        vint32m2_t t11 = __riscv_vwmul_vv_i32m2(z, y, vlc); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(seed, t0, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t1, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t2, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t3, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t4, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t5, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t6, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t7, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t8, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t9, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t10, vlc); \
        out = __riscv_vadd_vv_i32m2(out, t11, vlc); \
        out_big = __riscv_vset_v_i32m2_i32m8(out_big, K, out); \
    } \
} while (0)

    WB5_PHASE2_CHUNK_M1(0);
    WB5_PHASE2_CHUNK_M1(1);
    WB5_PHASE2_CHUNK_M1(2);
    WB5_PHASE2_CHUNK_M1(3);
#undef WB5_PHASE2_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb5_phase2[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb5_src2[offset], vl);
    vint32m8_t seed_big = __riscv_vle32_v_i32m8(&wb5_phase1[offset], vl);
    vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB5_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint16m2_t z = __riscv_vget_v_i16m4_i16m2(z_big, K); \
        vint32m4_t seed = __riscv_vget_v_i32m8_i32m4(seed_big, K); \
        vint32m4_t t0 = __riscv_vwadd_vv_i32m4(x, y, vlc); \
        vint32m4_t t1 = __riscv_vwmul_vv_i32m4(x, y, vlc); \
        vint32m4_t t2 = __riscv_vwadd_vv_i32m4(y, z, vlc); \
        vint32m4_t t3 = __riscv_vwmul_vv_i32m4(y, z, vlc); \
        vint32m4_t t4 = __riscv_vwadd_vv_i32m4(x, z, vlc); \
        vint32m4_t t5 = __riscv_vwmul_vv_i32m4(x, z, vlc); \
        vint32m4_t t6 = __riscv_vwadd_vv_i32m4(x, x, vlc); \
        vint32m4_t t7 = __riscv_vwadd_vv_i32m4(y, y, vlc); \
        vint32m4_t t8 = __riscv_vwmul_vv_i32m4(z, z, vlc); \
        vint32m4_t t9 = __riscv_vwmul_vv_i32m4(y, x, vlc); \
        vint32m4_t t10 = __riscv_vwadd_vv_i32m4(z, x, vlc); \
        vint32m4_t t11 = __riscv_vwmul_vv_i32m4(z, y, vlc); \
        vint32m4_t out = __riscv_vadd_vv_i32m4(seed, t0, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t1, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t2, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t3, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t4, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t5, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t6, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t7, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t8, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t9, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t10, vlc); \
        out = __riscv_vadd_vv_i32m4(out, t11, vlc); \
        out_big = __riscv_vset_v_i32m4_i32m8(out_big, K, out); \
    } \
} while (0)

    WB5_PHASE2_CHUNK_M2(0);
    WB5_PHASE2_CHUNK_M2(1);
#undef WB5_PHASE2_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb5_phase2[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb5_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb5_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb5_src1[offset], vl);
    vint16m4_t z = __riscv_vle16_v_i16m4(&wb5_src2[offset], vl);
    vint32m8_t seed = __riscv_vle32_v_i32m8(&wb5_phase1[offset], vl);
    vint32m8_t t0 = __riscv_vwadd_vv_i32m8(x, y, vl);
    vint32m8_t t1 = __riscv_vwmul_vv_i32m8(x, y, vl);
    vint32m8_t t2 = __riscv_vwadd_vv_i32m8(y, z, vl);
    vint32m8_t t3 = __riscv_vwmul_vv_i32m8(y, z, vl);
    vint32m8_t t4 = __riscv_vwadd_vv_i32m8(x, z, vl);
    vint32m8_t t5 = __riscv_vwmul_vv_i32m8(x, z, vl);
    vint32m8_t t6 = __riscv_vwadd_vv_i32m8(x, x, vl);
    vint32m8_t t7 = __riscv_vwadd_vv_i32m8(y, y, vl);
    vint32m8_t t8 = __riscv_vwmul_vv_i32m8(z, z, vl);
    vint32m8_t t9 = __riscv_vwmul_vv_i32m8(y, x, vl);
    vint32m8_t t10 = __riscv_vwadd_vv_i32m8(z, x, vl);
    vint32m8_t t11 = __riscv_vwmul_vv_i32m8(z, y, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(seed, t0, vl);
    out = __riscv_vadd_vv_i32m8(out, t1, vl);
    out = __riscv_vadd_vv_i32m8(out, t2, vl);
    out = __riscv_vadd_vv_i32m8(out, t3, vl);
    out = __riscv_vadd_vv_i32m8(out, t4, vl);
    out = __riscv_vadd_vv_i32m8(out, t5, vl);
    out = __riscv_vadd_vv_i32m8(out, t6, vl);
    out = __riscv_vadd_vv_i32m8(out, t7, vl);
    out = __riscv_vadd_vv_i32m8(out, t8, vl);
    out = __riscv_vadd_vv_i32m8(out, t9, vl);
    out = __riscv_vadd_vv_i32m8(out, t10, vl);
    out = __riscv_vadd_vv_i32m8(out, t11, vl);
    __riscv_vse32_v_i32m8(&wb5_phase2[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x_big = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y_big = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB5_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vint32m1_t x = __riscv_vget_v_i32m4_i32m1(x_big, K); \
        vint32m1_t y = __riscv_vget_v_i32m4_i32m1(y_big, K); \
        vint32m1_t out = __riscv_vadd_vv_i32m1(x, y, vlc); \
        out_big = __riscv_vset_v_i32m1_i32m4(out_big, K, out); \
    } \
} while (0)

    WB5_PHASE3_CHUNK_M1(0);
    WB5_PHASE3_CHUNK_M1(1);
    WB5_PHASE3_CHUNK_M1(2);
    WB5_PHASE3_CHUNK_M1(3);
#undef WB5_PHASE3_CHUNK_M1

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x_big = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y_big = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB5_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vint32m2_t x = __riscv_vget_v_i32m4_i32m2(x_big, K); \
        vint32m2_t y = __riscv_vget_v_i32m4_i32m2(y_big, K); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(x, y, vlc); \
        out_big = __riscv_vset_v_i32m2_i32m4(out_big, K, out); \
    } \
} while (0)

    WB5_PHASE3_CHUNK_M2(0);
    WB5_PHASE3_CHUNK_M2(1);
#undef WB5_PHASE3_CHUNK_M2

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb5_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t x = __riscv_vle32_v_i32m4(&wb5_phase1[offset], vl);
    vint32m4_t y = __riscv_vle32_v_i32m4(&wb5_phase2[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(x, y, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb5_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
