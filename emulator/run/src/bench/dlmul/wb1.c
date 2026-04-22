#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vin_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t shift_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t gate_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t sum_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    vfloat32m4_t mix_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB1_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t vin = __riscv_vget_v_f32m4_f32m1(vin_big, K); \
        vfloat32m1_t shift = __riscv_vget_v_f32m4_f32m1(shift_big, K); \
        vfloat32m1_t gate = __riscv_vget_v_f32m4_f32m1(gate_big, K); \
        vfloat32m1_t sum = __riscv_vfadd_vv_f32m1(vin, shift, vlc); \
        vfloat32m1_t mix = __riscv_vfmul_vv_f32m1(vin, gate, vlc); \
        sum_big = __riscv_vset_v_f32m1_f32m4(sum_big, K, sum); \
        mix_big = __riscv_vset_v_f32m1_f32m4(mix_big, K, mix); \
    } \
} while (0)

    WB1_PHASE1_CHUNK_M1(0);
    WB1_PHASE1_CHUNK_M1(1);
    WB1_PHASE1_CHUNK_M1(2);
    WB1_PHASE1_CHUNK_M1(3);
#undef WB1_PHASE1_CHUNK_M1

    __riscv_vse32_v_f32m4(&d[offset], sum_big, vl);
    __riscv_vse32_v_f32m4(&e[offset], mix_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vin_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t shift_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t gate_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t sum_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    vfloat32m4_t mix_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB1_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t vin = __riscv_vget_v_f32m4_f32m2(vin_big, K); \
        vfloat32m2_t shift = __riscv_vget_v_f32m4_f32m2(shift_big, K); \
        vfloat32m2_t gate = __riscv_vget_v_f32m4_f32m2(gate_big, K); \
        vfloat32m2_t sum = __riscv_vfadd_vv_f32m2(vin, shift, vlc); \
        vfloat32m2_t mix = __riscv_vfmul_vv_f32m2(vin, gate, vlc); \
        sum_big = __riscv_vset_v_f32m2_f32m4(sum_big, K, sum); \
        mix_big = __riscv_vset_v_f32m2_f32m4(mix_big, K, mix); \
    } \
} while (0)

    WB1_PHASE1_CHUNK_M2(0);
    WB1_PHASE1_CHUNK_M2(1);
#undef WB1_PHASE1_CHUNK_M2

    __riscv_vse32_v_f32m4(&d[offset], sum_big, vl);
    __riscv_vse32_v_f32m4(&e[offset], mix_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t vin = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t shift = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t gate = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t sum = __riscv_vfadd_vv_f32m4(vin, shift, vl);
    vfloat32m4_t mix = __riscv_vfmul_vv_f32m4(vin, gate, vl);
    __riscv_vse32_v_f32m4(&d[offset], sum, vl);
    __riscv_vse32_v_f32m4(&e[offset], mix, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t sum_big = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t mix_big = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t scale_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t bias_big = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB1_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t sum = __riscv_vget_v_f32m4_f32m1(sum_big, K); \
        vfloat32m1_t mix = __riscv_vget_v_f32m4_f32m1(mix_big, K); \
        vfloat32m1_t scale = __riscv_vget_v_f32m4_f32m1(scale_big, K); \
        vfloat32m1_t bias = __riscv_vget_v_f32m4_f32m1(bias_big, K); \
        vfloat32m1_t centered = __riscv_vfsub_vv_f32m1(sum, bias, vlc); \
        vfloat32m1_t scaled = __riscv_vfmul_vv_f32m1(centered, scale, vlc); \
        vfloat32m1_t out = __riscv_vfadd_vv_f32m1(scaled, mix, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, sum, vlc); \
        out_big = __riscv_vset_v_f32m1_f32m4(out_big, K, out); \
    } \
} while (0)

    WB1_PHASE2_CHUNK_M1(0);
    WB1_PHASE2_CHUNK_M1(1);
    WB1_PHASE2_CHUNK_M1(2);
    WB1_PHASE2_CHUNK_M1(3);
#undef WB1_PHASE2_CHUNK_M1

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t sum_big = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t mix_big = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t scale_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t bias_big = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB1_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t sum = __riscv_vget_v_f32m4_f32m2(sum_big, K); \
        vfloat32m2_t mix = __riscv_vget_v_f32m4_f32m2(mix_big, K); \
        vfloat32m2_t scale = __riscv_vget_v_f32m4_f32m2(scale_big, K); \
        vfloat32m2_t bias = __riscv_vget_v_f32m4_f32m2(bias_big, K); \
        vfloat32m2_t centered = __riscv_vfsub_vv_f32m2(sum, bias, vlc); \
        vfloat32m2_t scaled = __riscv_vfmul_vv_f32m2(centered, scale, vlc); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(scaled, mix, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, sum, vlc); \
        out_big = __riscv_vset_v_f32m2_f32m4(out_big, K, out); \
    } \
} while (0)

    WB1_PHASE2_CHUNK_M2(0);
    WB1_PHASE2_CHUNK_M2(1);
#undef WB1_PHASE2_CHUNK_M2

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t sum = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t mix = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t scale = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t bias = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t centered = __riscv_vfsub_vv_f32m4(sum, bias, vl);
    vfloat32m4_t scaled = __riscv_vfmul_vv_f32m4(centered, scale, vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(scaled, mix, vl);
    out = __riscv_vfadd_vv_f32m4(out, sum, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB1_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t fused = __riscv_vget_v_f32m4_f32m1(fused_big, K); \
        vfloat32m1_t affine = __riscv_vget_v_f32m4_f32m1(affine_big, K); \
        vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(affine, 0.5f, fused, vlc); \
        out_big = __riscv_vset_v_f32m1_f32m4(out_big, K, out); \
    } \
} while (0)

    WB1_PHASE3_CHUNK_M1(0);
    WB1_PHASE3_CHUNK_M1(1);
    WB1_PHASE3_CHUNK_M1(2);
    WB1_PHASE3_CHUNK_M1(3);
#undef WB1_PHASE3_CHUNK_M1

    __riscv_vse32_v_f32m4(&a[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB1_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t fused = __riscv_vget_v_f32m4_f32m2(fused_big, K); \
        vfloat32m2_t affine = __riscv_vget_v_f32m4_f32m2(affine_big, K); \
        vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(affine, 0.5f, fused, vlc); \
        out_big = __riscv_vset_v_f32m2_f32m4(out_big, K, out); \
    } \
} while (0)

    WB1_PHASE3_CHUNK_M2(0);
    WB1_PHASE3_CHUNK_M2(1);
#undef WB1_PHASE3_CHUNK_M2

    __riscv_vse32_v_f32m4(&a[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb1_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(affine, 0.5f, fused, vl);
    __riscv_vse32_v_f32m4(&a[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE3_VARIANT"
#endif

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < DLB_OUTER_ITERS; ++iter) {
        int offset = 0;
        int remaining = DLB_PHASE1_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb1_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb1_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb1_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
