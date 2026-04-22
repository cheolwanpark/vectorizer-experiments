#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb2_activation[LEN_1D];
static int16_t wb2_weight[LEN_1D];
static int16_t wb2_bias16[LEN_1D];
static int32_t wb2_partial[LEN_1D];
static int32_t wb2_output[LEN_1D];

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act_big = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt_big = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint32m8_t widened_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB2_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t act = __riscv_vget_v_i16m4_i16m1(act_big, K); \
        vint16m1_t wt = __riscv_vget_v_i16m4_i16m1(wt_big, K); \
        vint32m2_t widened = __riscv_vwadd_vv_i32m2(act, wt, vlc); \
        widened_big = __riscv_vset_v_i32m2_i32m8(widened_big, K, widened); \
    } \
} while (0)

    WB2_PHASE1_CHUNK_M1(0);
    WB2_PHASE1_CHUNK_M1(1);
    WB2_PHASE1_CHUNK_M1(2);
    WB2_PHASE1_CHUNK_M1(3);
#undef WB2_PHASE1_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb2_partial[offset], widened_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act_big = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt_big = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint32m8_t widened_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB2_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t act = __riscv_vget_v_i16m4_i16m2(act_big, K); \
        vint16m2_t wt = __riscv_vget_v_i16m4_i16m2(wt_big, K); \
        vint32m4_t widened = __riscv_vwadd_vv_i32m4(act, wt, vlc); \
        widened_big = __riscv_vset_v_i32m4_i32m8(widened_big, K, widened); \
    } \
} while (0)

    WB2_PHASE1_CHUNK_M2(0);
    WB2_PHASE1_CHUNK_M2(1);
#undef WB2_PHASE1_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb2_partial[offset], widened_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint32m8_t widened = __riscv_vwadd_vv_i32m8(act, wt, vl);
    __riscv_vse32_v_i32m8(&wb2_partial[offset], widened, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act_big = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt_big = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint16m4_t bias_big = __riscv_vle16_v_i16m4(&wb2_bias16[offset], vl);
    vint32m8_t partial_big = __riscv_vle32_v_i32m8(&wb2_partial[offset], vl);
    vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m1(avl);

#define WB2_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m1(avl - start); \
        vint16m1_t act = __riscv_vget_v_i16m4_i16m1(act_big, K); \
        vint16m1_t wt = __riscv_vget_v_i16m4_i16m1(wt_big, K); \
        vint16m1_t bias = __riscv_vget_v_i16m4_i16m1(bias_big, K); \
        vint32m2_t partial = __riscv_vget_v_i32m8_i32m2(partial_big, K); \
        vint32m2_t acc0 = __riscv_vwmul_vv_i32m2(act, wt, vlc); \
        vint32m2_t acc1 = __riscv_vwmul_vv_i32m2(act, bias, vlc); \
        vint32m2_t acc2 = __riscv_vwmul_vv_i32m2(wt, bias, vlc); \
        vint32m2_t out = __riscv_vadd_vv_i32m2(partial, acc0, vlc); \
        out = __riscv_vadd_vv_i32m2(out, acc1, vlc); \
        out = __riscv_vadd_vv_i32m2(out, acc2, vlc); \
        out_big = __riscv_vset_v_i32m2_i32m8(out_big, K, out); \
    } \
} while (0)

    WB2_PHASE2_CHUNK_M1(0);
    WB2_PHASE2_CHUNK_M1(1);
    WB2_PHASE2_CHUNK_M1(2);
    WB2_PHASE2_CHUNK_M1(3);
#undef WB2_PHASE2_CHUNK_M1

    __riscv_vse32_v_i32m8(&wb2_output[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act_big = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt_big = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint16m4_t bias_big = __riscv_vle16_v_i16m4(&wb2_bias16[offset], vl);
    vint32m8_t partial_big = __riscv_vle32_v_i32m8(&wb2_partial[offset], vl);
    vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, vl);
    size_t chunk = __riscv_vsetvl_e16m2(avl);

#define WB2_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e16m2(avl - start); \
        vint16m2_t act = __riscv_vget_v_i16m4_i16m2(act_big, K); \
        vint16m2_t wt = __riscv_vget_v_i16m4_i16m2(wt_big, K); \
        vint16m2_t bias = __riscv_vget_v_i16m4_i16m2(bias_big, K); \
        vint32m4_t partial = __riscv_vget_v_i32m8_i32m4(partial_big, K); \
        vint32m4_t acc0 = __riscv_vwmul_vv_i32m4(act, wt, vlc); \
        vint32m4_t acc1 = __riscv_vwmul_vv_i32m4(act, bias, vlc); \
        vint32m4_t acc2 = __riscv_vwmul_vv_i32m4(wt, bias, vlc); \
        vint32m4_t out = __riscv_vadd_vv_i32m4(partial, acc0, vlc); \
        out = __riscv_vadd_vv_i32m4(out, acc1, vlc); \
        out = __riscv_vadd_vv_i32m4(out, acc2, vlc); \
        out_big = __riscv_vset_v_i32m4_i32m8(out_big, K, out); \
    } \
} while (0)

    WB2_PHASE2_CHUNK_M2(0);
    WB2_PHASE2_CHUNK_M2(1);
#undef WB2_PHASE2_CHUNK_M2

    __riscv_vse32_v_i32m8(&wb2_output[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e16m4(avl);
    vint16m4_t act = __riscv_vle16_v_i16m4(&wb2_activation[offset], vl);
    vint16m4_t wt = __riscv_vle16_v_i16m4(&wb2_weight[offset], vl);
    vint16m4_t bias = __riscv_vle16_v_i16m4(&wb2_bias16[offset], vl);
    vint32m8_t partial = __riscv_vle32_v_i32m8(&wb2_partial[offset], vl);
    vint32m8_t acc0 = __riscv_vwmul_vv_i32m8(act, wt, vl);
    vint32m8_t acc1 = __riscv_vwmul_vv_i32m8(act, bias, vl);
    vint32m8_t acc2 = __riscv_vwmul_vv_i32m8(wt, bias, vl);
    vint32m8_t out = __riscv_vadd_vv_i32m8(partial, acc0, vl);
    out = __riscv_vadd_vv_i32m8(out, acc1, vl);
    out = __riscv_vadd_vv_i32m8(out, acc2, vl);
    __riscv_vse32_v_i32m8(&wb2_output[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t out_big = __riscv_vle32_v_i32m4(&wb2_output[offset], vl);
    vint32m4_t partial_big = __riscv_vle32_v_i32m4(&wb2_partial[offset], vl);
    vint32m4_t fused_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB2_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vint32m1_t out = __riscv_vget_v_i32m4_i32m1(out_big, K); \
        vint32m1_t partial = __riscv_vget_v_i32m4_i32m1(partial_big, K); \
        vint32m1_t fused = __riscv_vadd_vv_i32m1(out, partial, vlc); \
        fused_big = __riscv_vset_v_i32m1_i32m4(fused_big, K, fused); \
    } \
} while (0)

    WB2_PHASE3_CHUNK_M1(0);
    WB2_PHASE3_CHUNK_M1(1);
    WB2_PHASE3_CHUNK_M1(2);
    WB2_PHASE3_CHUNK_M1(3);
#undef WB2_PHASE3_CHUNK_M1

    __riscv_vse32_v_i32m4(&indx[offset], fused_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t out_big = __riscv_vle32_v_i32m4(&wb2_output[offset], vl);
    vint32m4_t partial_big = __riscv_vle32_v_i32m4(&wb2_partial[offset], vl);
    vint32m4_t fused_big = __riscv_vmv_v_x_i32m4(0, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB2_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vint32m2_t out = __riscv_vget_v_i32m4_i32m2(out_big, K); \
        vint32m2_t partial = __riscv_vget_v_i32m4_i32m2(partial_big, K); \
        vint32m2_t fused = __riscv_vadd_vv_i32m2(out, partial, vlc); \
        fused_big = __riscv_vset_v_i32m2_i32m4(fused_big, K, fused); \
    } \
} while (0)

    WB2_PHASE3_CHUNK_M2(0);
    WB2_PHASE3_CHUNK_M2(1);
#undef WB2_PHASE3_CHUNK_M2

    __riscv_vse32_v_i32m4(&indx[offset], fused_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb2_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vint32m4_t out = __riscv_vle32_v_i32m4(&wb2_output[offset], vl);
    vint32m4_t partial = __riscv_vle32_v_i32m4(&wb2_partial[offset], vl);
    vint32m4_t fused = __riscv_vadd_vv_i32m4(out, partial, vl);
    __riscv_vse32_v_i32m4(&indx[offset], fused, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_int16_triplet(wb2_activation, wb2_weight, wb2_bias16, LEN_1D);
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb2_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb2_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb2_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
