#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb7_src0[LEN_1D];
static int16_t wb7_src1[LEN_1D];
static int16_t wb7_src2[LEN_1D];
static int32_t wb7_base[LEN_1D];
static int32_t wb7_poly[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb7_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint32m8_t base_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB7_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint32m2_t base = __riscv_vwadd_vv_i32m2(x, y, vlc); \
        base_big = __riscv_vset_v_i32m2_i32m8(base_big, K, base); \
    } \
} while (0)

    WB7_PHASE1_CHUNK_M1(0);
    WB7_PHASE1_CHUNK_M1(1);
    WB7_PHASE1_CHUNK_M1(2);
    WB7_PHASE1_CHUNK_M1(3);
#undef WB7_PHASE1_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb7_base[offset], base_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb7_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint32m8_t base_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB7_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint32m4_t base = __riscv_vwadd_vv_i32m4(x, y, vlc); \
        base_big = __riscv_vset_v_i32m4_i32m8(base_big, K, base); \
    } \
} while (0)

    WB7_PHASE1_CHUNK_M2(0);
    WB7_PHASE1_CHUNK_M2(1);
#undef WB7_PHASE1_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb7_base[offset], base_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb7_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint32m8_t base = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb7_base[offset], base, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb7_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb7_src2[offset], vl);
    vint32m8_t base_big = __riscv_vle32_v_i32m8(&wb7_base[offset], vl);
    vint32m8_t poly_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB7_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint16m1_t z = __riscv_vget_v_i16m4_i16m1(z_big, K); \
        vint32m2_t base = __riscv_vget_v_i32m8_i32m2(base_big, K); \
        vint32m2_t sq = __riscv_vwmul_vv_i32m2(x, x, vlc); \
        vint32m2_t cross = __riscv_vwmul_vv_i32m2(y, z, vlc); \
        vint32m2_t mix = __riscv_vwmul_vv_i32m2(x, z, vlc); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(base, sq, vlc); \
        out = __riscv_vadd_vv_i32m2(out, cross, vlc); \
        out = __riscv_vsub_vv_i32m2(out, mix, vlc); \
        poly_big = __riscv_vset_v_i32m2_i32m8(poly_big, K, out); \
    } \
} while (0)

    WB7_PHASE2_CHUNK_M1(0);
    WB7_PHASE2_CHUNK_M1(1);
    WB7_PHASE2_CHUNK_M1(2);
    WB7_PHASE2_CHUNK_M1(3);
#undef WB7_PHASE2_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb7_poly[offset], poly_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb7_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb7_src2[offset], vl);
    vint32m8_t base_big = __riscv_vle32_v_i32m8(&wb7_base[offset], vl);
    vint32m8_t poly_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB7_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint16m2_t z = __riscv_vget_v_i16m4_i16m2(z_big, K); \
        vint32m4_t base = __riscv_vget_v_i32m8_i32m4(base_big, K); \
        vint32m4_t sq = __riscv_vwmul_vv_i32m4(x, x, vlc); \
        vint32m4_t cross = __riscv_vwmul_vv_i32m4(y, z, vlc); \
        vint32m4_t mix = __riscv_vwmul_vv_i32m4(x, z, vlc); \
        vint32m4_t out = __riscv_vadd_vv_i32m4(base, sq, vlc); \
        out = __riscv_vadd_vv_i32m4(out, cross, vlc); \
        out = __riscv_vsub_vv_i32m4(out, mix, vlc); \
        poly_big = __riscv_vset_v_i32m4_i32m8(poly_big, K, out); \
    } \
} while (0)

    WB7_PHASE2_CHUNK_M2(0);
    WB7_PHASE2_CHUNK_M2(1);
#undef WB7_PHASE2_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb7_poly[offset], poly_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb7_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb7_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb7_src1[offset], vl);
    vint16m4_t z = __riscv_vle16_v_i16m4(&wb7_src2[offset], vl);
    vint32m8_t base = __riscv_vle32_v_i32m8(&wb7_base[offset], vl);
    vint32m8_t sq = __riscv_vwmul_vv_i32m8(x, x, vl);
    vint32m8_t cross = __riscv_vwmul_vv_i32m8(y, z, vl);
    vint32m8_t mix = __riscv_vwmul_vv_i32m8(x, z, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(base, sq, vl);
    out = __riscv_vadd_vv_i32m8(out, cross, vl);
    out = __riscv_vsub_vv_i32m8(out, mix, vl);
    __riscv_vse32_v_i32m8(&wb7_poly[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb7_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t base_big = __riscv_vle32_v_i32m4(&wb7_base[offset], vl);
    vint32m4_t poly_big = __riscv_vle32_v_i32m4(&wb7_poly[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB7_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vint32m1_t base = __riscv_vget_v_i32m4_i32m1(base_big, K); \
        vint32m1_t poly = __riscv_vget_v_i32m4_i32m1(poly_big, K); \
        vint32m1_t out = __riscv_vadd_vv_i32m1(base, poly, vlc); \
        out_big = __riscv_vset_v_i32m1_i32m4(out_big, K, out); \
    } \
} while (0)

    WB7_PHASE3_CHUNK_M1(0);
    WB7_PHASE3_CHUNK_M1(1);
    WB7_PHASE3_CHUNK_M1(2);
    WB7_PHASE3_CHUNK_M1(3);
#undef WB7_PHASE3_CHUNK_M1

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb7_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t base_big = __riscv_vle32_v_i32m4(&wb7_base[offset], vl);
    vint32m4_t poly_big = __riscv_vle32_v_i32m4(&wb7_poly[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB7_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vint32m2_t base = __riscv_vget_v_i32m4_i32m2(base_big, K); \
        vint32m2_t poly = __riscv_vget_v_i32m4_i32m2(poly_big, K); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(base, poly, vlc); \
        out_big = __riscv_vset_v_i32m2_i32m4(out_big, K, out); \
    } \
} while (0)

    WB7_PHASE3_CHUNK_M2(0);
    WB7_PHASE3_CHUNK_M2(1);
#undef WB7_PHASE3_CHUNK_M2

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb7_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t base = __riscv_vle32_v_i32m4(&wb7_base[offset], vl);
    vint32m4_t poly = __riscv_vle32_v_i32m4(&wb7_poly[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(base, poly, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb7_src0, wb7_src1, wb7_src2, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb7_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb7_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb7_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
