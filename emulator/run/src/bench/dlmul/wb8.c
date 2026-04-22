#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb8_src0[LEN_1D];
static int16_t wb8_src1[LEN_1D];
static int16_t wb8_src2[LEN_1D];
static int32_t wb8_seed[LEN_1D];
static int32_t wb8_left[LEN_1D];
static int32_t wb8_right[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb8_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint32m8_t seed_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB8_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint32m2_t seed = __riscv_vwadd_vv_i32m2(x, y, vlc); \
        seed_big = __riscv_vset_v_i32m2_i32m8(seed_big, K, seed); \
    } \
} while (0)

    WB8_PHASE1_CHUNK_M1(0);
    WB8_PHASE1_CHUNK_M1(1);
    WB8_PHASE1_CHUNK_M1(2);
    WB8_PHASE1_CHUNK_M1(3);
#undef WB8_PHASE1_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb8_seed[offset], seed_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb8_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint32m8_t seed_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB8_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint32m4_t seed = __riscv_vwadd_vv_i32m4(x, y, vlc); \
        seed_big = __riscv_vset_v_i32m4_i32m8(seed_big, K, seed); \
    } \
} while (0)

    WB8_PHASE1_CHUNK_M2(0);
    WB8_PHASE1_CHUNK_M2(1);
#undef WB8_PHASE1_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb8_seed[offset], seed_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb8_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint32m8_t seed = __riscv_vwadd_vv_i32m8(x, y, vl);
    __riscv_vse32_v_i32m8(&wb8_seed[offset], seed, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb8_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb8_src2[offset], vl);
    vint32m8_t seed_big = __riscv_vle32_v_i32m8(&wb8_seed[offset], vl);
    vint32m8_t left_big = __riscv_vmv_v_x_i32m8(0, vl);
    vint32m8_t right_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB8_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t x = __riscv_vget_v_i16m4_i16m1(x_big, K); \
        vint16m1_t y = __riscv_vget_v_i16m4_i16m1(y_big, K); \
        vint16m1_t z = __riscv_vget_v_i16m4_i16m1(z_big, K); \
        vint32m2_t seed = __riscv_vget_v_i32m8_i32m2(seed_big, K); \
        vint32m2_t left = __riscv_vadd_vv_i32m2(seed, __riscv_vwmul_vv_i32m2(x, y, vlc), vlc); \
        vint32m2_t right = __riscv_vadd_vv_i32m2(seed, __riscv_vwmul_vv_i32m2(x, z, vlc), vlc); \
        left = __riscv_vadd_vv_i32m2(left, __riscv_vwadd_vv_i32m2(y, z, vlc), vlc); \
        right = __riscv_vadd_vv_i32m2(right, __riscv_vwmul_vv_i32m2(y, y, vlc), vlc); \
        left_big = __riscv_vset_v_i32m2_i32m8(left_big, K, left); \
        right_big = __riscv_vset_v_i32m2_i32m8(right_big, K, right); \
    } \
} while (0)

    WB8_PHASE2_CHUNK_M1(0);
    WB8_PHASE2_CHUNK_M1(1);
    WB8_PHASE2_CHUNK_M1(2);
    WB8_PHASE2_CHUNK_M1(3);
#undef WB8_PHASE2_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb8_left[offset], left_big, vl);
    __riscv_vse32_v_i32m8(&wb8_right[offset], right_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb8_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb8_src2[offset], vl);
    vint32m8_t seed_big = __riscv_vle32_v_i32m8(&wb8_seed[offset], vl);
    vint32m8_t left_big = __riscv_vmv_v_x_i32m8(0, vl);
    vint32m8_t right_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB8_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t x = __riscv_vget_v_i16m4_i16m2(x_big, K); \
        vint16m2_t y = __riscv_vget_v_i16m4_i16m2(y_big, K); \
        vint16m2_t z = __riscv_vget_v_i16m4_i16m2(z_big, K); \
        vint32m4_t seed = __riscv_vget_v_i32m8_i32m4(seed_big, K); \
        vint32m4_t left = __riscv_vadd_vv_i32m4(seed, __riscv_vwmul_vv_i32m4(x, y, vlc), vlc); \
        vint32m4_t right = __riscv_vadd_vv_i32m4(seed, __riscv_vwmul_vv_i32m4(x, z, vlc), vlc); \
        left = __riscv_vadd_vv_i32m4(left, __riscv_vwadd_vv_i32m4(y, z, vlc), vlc); \
        right = __riscv_vadd_vv_i32m4(right, __riscv_vwmul_vv_i32m4(y, y, vlc), vlc); \
        left_big = __riscv_vset_v_i32m4_i32m8(left_big, K, left); \
        right_big = __riscv_vset_v_i32m4_i32m8(right_big, K, right); \
    } \
} while (0)

    WB8_PHASE2_CHUNK_M2(0);
    WB8_PHASE2_CHUNK_M2(1);
#undef WB8_PHASE2_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb8_left[offset], left_big, vl);
    __riscv_vse32_v_i32m8(&wb8_right[offset], right_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb8_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t x = __riscv_vle16_v_i16m4(&wb8_src0[offset], vl);
    vint16m4_t y = __riscv_vle16_v_i16m4(&wb8_src1[offset], vl);
    vint16m4_t z = __riscv_vle16_v_i16m4(&wb8_src2[offset], vl);
    vint32m8_t seed = __riscv_vle32_v_i32m8(&wb8_seed[offset], vl);
    vint32m8_t left = __riscv_vadd_vv_i32m8(seed, __riscv_vwmul_vv_i32m8(x, y, vl), vl);
    vint32m8_t right = __riscv_vadd_vv_i32m8(seed, __riscv_vwmul_vv_i32m8(x, z, vl), vl);
    left = __riscv_vadd_vv_i32m8(left, __riscv_vwadd_vv_i32m8(y, z, vl), vl);
    right = __riscv_vadd_vv_i32m8(right, __riscv_vwmul_vv_i32m8(y, y, vl), vl);
    __riscv_vse32_v_i32m8(&wb8_left[offset], left, vl);
    __riscv_vse32_v_i32m8(&wb8_right[offset], right, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb8_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t left_big = __riscv_vle32_v_i32m4(&wb8_left[offset], vl);
    vint32m4_t right_big = __riscv_vle32_v_i32m4(&wb8_right[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB8_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vint32m1_t left = __riscv_vget_v_i32m4_i32m1(left_big, K); \
        vint32m1_t right = __riscv_vget_v_i32m4_i32m1(right_big, K); \
        vint32m1_t out = __riscv_vadd_vv_i32m1(left, right, vlc); \
        out_big = __riscv_vset_v_i32m1_i32m4(out_big, K, out); \
    } \
} while (0)

    WB8_PHASE3_CHUNK_M1(0);
    WB8_PHASE3_CHUNK_M1(1);
    WB8_PHASE3_CHUNK_M1(2);
    WB8_PHASE3_CHUNK_M1(3);
#undef WB8_PHASE3_CHUNK_M1

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb8_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t left_big = __riscv_vle32_v_i32m4(&wb8_left[offset], vl);
    vint32m4_t right_big = __riscv_vle32_v_i32m4(&wb8_right[offset], vl);
    vint32m4_t out_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB8_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vint32m2_t left = __riscv_vget_v_i32m4_i32m2(left_big, K); \
        vint32m2_t right = __riscv_vget_v_i32m4_i32m2(right_big, K); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(left, right, vlc); \
        out_big = __riscv_vset_v_i32m2_i32m4(out_big, K, out); \
    } \
} while (0)

    WB8_PHASE3_CHUNK_M2(0);
    WB8_PHASE3_CHUNK_M2(1);
#undef WB8_PHASE3_CHUNK_M2

    __riscv_vse32_v_i32m4(&indx[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb8_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t left = __riscv_vle32_v_i32m4(&wb8_left[offset], vl);
    vint32m4_t right = __riscv_vle32_v_i32m4(&wb8_right[offset], vl);
    vint32m4_t out = __riscv_vadd_vv_i32m4(left, right, vl);
    __riscv_vse32_v_i32m4(&indx[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb8_src0, wb8_src1, wb8_src2, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb8_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb8_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb8_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
