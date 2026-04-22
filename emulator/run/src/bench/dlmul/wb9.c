#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#if DLB_PHASE1_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t x0_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t seed_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB9_PHASE1_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t x0 = __riscv_vget_v_f32m4_f32m1(x0_big, K); \
        vfloat32m1_t x1 = __riscv_vget_v_f32m4_f32m1(x1_big, K); \
        vfloat32m1_t seed = __riscv_vfadd_vv_f32m1(x0, x1, vlc); \
        seed_big = __riscv_vset_v_f32m1_f32m4(seed_big, K, seed); \
    } \
} while (0)

    WB9_PHASE1_CHUNK_M1(0);
    WB9_PHASE1_CHUNK_M1(1);
    WB9_PHASE1_CHUNK_M1(2);
    WB9_PHASE1_CHUNK_M1(3);
#undef WB9_PHASE1_CHUNK_M1

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], seed_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t x0_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t seed_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB9_PHASE1_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t x0 = __riscv_vget_v_f32m4_f32m2(x0_big, K); \
        vfloat32m2_t x1 = __riscv_vget_v_f32m4_f32m2(x1_big, K); \
        vfloat32m2_t seed = __riscv_vfadd_vv_f32m2(x0, x1, vlc); \
        seed_big = __riscv_vset_v_f32m2_f32m4(seed_big, K, seed); \
    } \
} while (0)

    WB9_PHASE1_CHUNK_M2(0);
    WB9_PHASE1_CHUNK_M2(1);
#undef WB9_PHASE1_CHUNK_M2

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], seed_big, vl);
    return vl;
}
#elif DLB_PHASE1_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase1_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t x0 = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t seed = __riscv_vfadd_vv_f32m4(x0, x1, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], seed, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE1_VARIANT"
#endif

#if DLB_PHASE2_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t seed_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t x0_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t x2_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t x3_big = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t x4_big = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t x5_big = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB9_PHASE2_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t seed = __riscv_vget_v_f32m4_f32m1(seed_big, K); \
        vfloat32m1_t x0 = __riscv_vget_v_f32m4_f32m1(x0_big, K); \
        vfloat32m1_t x1 = __riscv_vget_v_f32m4_f32m1(x1_big, K); \
        vfloat32m1_t x2 = __riscv_vget_v_f32m4_f32m1(x2_big, K); \
        vfloat32m1_t x3 = __riscv_vget_v_f32m4_f32m1(x3_big, K); \
        vfloat32m1_t x4 = __riscv_vget_v_f32m4_f32m1(x4_big, K); \
        vfloat32m1_t x5 = __riscv_vget_v_f32m4_f32m1(x5_big, K); \
        vfloat32m1_t out = __riscv_vfadd_vv_f32m1(seed, x0, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, x1, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, x2, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, x3, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, x4, vlc); \
        out = __riscv_vfadd_vv_f32m1(out, x5, vlc); \
        out_big = __riscv_vset_v_f32m1_f32m4(out_big, K, out); \
    } \
} while (0)

    WB9_PHASE2_CHUNK_M1(0);
    WB9_PHASE2_CHUNK_M1(1);
    WB9_PHASE2_CHUNK_M1(2);
    WB9_PHASE2_CHUNK_M1(3);
#undef WB9_PHASE2_CHUNK_M1

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t seed_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t x0_big = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t x2_big = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t x3_big = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t x4_big = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t x5_big = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB9_PHASE2_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t seed = __riscv_vget_v_f32m4_f32m2(seed_big, K); \
        vfloat32m2_t x0 = __riscv_vget_v_f32m4_f32m2(x0_big, K); \
        vfloat32m2_t x1 = __riscv_vget_v_f32m4_f32m2(x1_big, K); \
        vfloat32m2_t x2 = __riscv_vget_v_f32m4_f32m2(x2_big, K); \
        vfloat32m2_t x3 = __riscv_vget_v_f32m4_f32m2(x3_big, K); \
        vfloat32m2_t x4 = __riscv_vget_v_f32m4_f32m2(x4_big, K); \
        vfloat32m2_t x5 = __riscv_vget_v_f32m4_f32m2(x5_big, K); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(seed, x0, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, x1, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, x2, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, x3, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, x4, vlc); \
        out = __riscv_vfadd_vv_f32m2(out, x5, vlc); \
        out_big = __riscv_vset_v_f32m2_f32m4(out_big, K, out); \
    } \
} while (0)

    WB9_PHASE2_CHUNK_M2(0);
    WB9_PHASE2_CHUNK_M2(1);
#undef WB9_PHASE2_CHUNK_M2

    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE2_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase2_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t seed = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t x0 = __riscv_vle32_v_f32m4(&a[offset], vl);
    vfloat32m4_t x1 = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t x2 = __riscv_vle32_v_f32m4(&c[offset], vl);
    vfloat32m4_t x3 = __riscv_vle32_v_f32m4(&d[offset], vl);
    vfloat32m4_t x4 = __riscv_vle32_v_f32m4(&e[offset], vl);
    vfloat32m4_t x5 = __riscv_vle32_v_f32m4(&x[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(seed, x0, vl);
    out = __riscv_vfadd_vv_f32m4(out, x1, vl);
    out = __riscv_vfadd_vv_f32m4(out, x2, vl);
    out = __riscv_vfadd_vv_f32m4(out, x3, vl);
    out = __riscv_vfadd_vv_f32m4(out, x4, vl);
    out = __riscv_vfadd_vv_f32m4(out, x5, vl);
    __riscv_vse32_v_f32m4(&flat_2d_array[offset], out, vl);
    return vl;
}
#else
#error "unsupported DLB_PHASE2_VARIANT"
#endif

#if DLB_PHASE3_VARIANT == DLMUL_LMUL_M1
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m1(avl);

#define WB9_PHASE3_CHUNK_M1(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m1(avl - start); \
        vfloat32m1_t fused = __riscv_vget_v_f32m4_f32m1(fused_big, K); \
        vfloat32m1_t affine = __riscv_vget_v_f32m4_f32m1(affine_big, K); \
        vfloat32m1_t out = __riscv_vfadd_vv_f32m1(fused, affine, vlc); \
        out_big = __riscv_vset_v_f32m1_f32m4(out_big, K, out); \
    } \
} while (0)

    WB9_PHASE3_CHUNK_M1(0);
    WB9_PHASE3_CHUNK_M1(1);
    WB9_PHASE3_CHUNK_M1(2);
    WB9_PHASE3_CHUNK_M1(3);
#undef WB9_PHASE3_CHUNK_M1

    __riscv_vse32_v_f32m4(&a[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M2
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused_big = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine_big = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, vl);
    size_t chunk = __riscv_vsetvl_e32m2(avl);

#define WB9_PHASE3_CHUNK_M2(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t fused = __riscv_vget_v_f32m4_f32m2(fused_big, K); \
        vfloat32m2_t affine = __riscv_vget_v_f32m4_f32m2(affine_big, K); \
        vfloat32m2_t out = __riscv_vfadd_vv_f32m2(fused, affine, vlc); \
        out_big = __riscv_vset_v_f32m2_f32m4(out_big, K, out); \
    } \
} while (0)

    WB9_PHASE3_CHUNK_M2(0);
    WB9_PHASE3_CHUNK_M2(1);
#undef WB9_PHASE3_CHUNK_M2

    __riscv_vse32_v_f32m4(&a[offset], out_big, vl);
    return vl;
}
#elif DLB_PHASE3_VARIANT == DLMUL_LMUL_M4
static __attribute__((noinline)) size_t wb9_phase3_step(int offset, size_t avl) {
    size_t vl = __riscv_vsetvl_e32m4(avl);
    vfloat32m4_t fused = __riscv_vle32_v_f32m4(&flat_2d_array[offset], vl);
    vfloat32m4_t affine = __riscv_vle32_v_f32m4(&b[offset], vl);
    vfloat32m4_t out = __riscv_vfadd_vv_f32m4(fused, affine, vl);
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
            size_t vl = wb9_phase1_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE2_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb9_phase2_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }

        offset = 0;
        remaining = DLB_PHASE3_TOTAL_ELEMS;
        while (remaining > 0) {
            size_t vl = wb9_phase3_step(offset, (size_t)remaining);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
