#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_MAIN
#endif

#define WB11_TOTAL_ELEMS 192
#define WB11_OUTER_ITERS 30

#define WB11_RUN_FIXED(lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < WB11_OUTER_ITERS; ++iter) { \
        int offset = 0; \
        int remaining = WB11_TOTAL_ELEMS; \
        while (remaining > 0) { \
            size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
            DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
            DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
            DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
            DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
            DLB_F32_T(lmul) ve = DLB_VLE32(lmul)(&e[offset], vl); \
            DLB_F32_T(lmul) vx = DLB_VLE32(lmul)(&x[offset], vl); \
            DLB_F32_T(lmul) pre0 = DLB_VFADD(lmul)(va, vb, vl); \
            DLB_F32_T(lmul) pre1 = DLB_VFMUL(lmul)(vc, vd, vl); \
            DLB_F32_T(lmul) t0 = DLB_VFSUB(lmul)(pre0, vx, vl); \
            DLB_F32_T(lmul) t1 = DLB_VFMUL(lmul)(t0, vc, vl); \
            DLB_F32_T(lmul) t2 = DLB_VFADD(lmul)(t1, pre1, vl); \
            DLB_F32_T(lmul) t3 = DLB_VFMACC_VF(lmul)(t2, 0.5f, vd, vl); \
            DLB_F32_T(lmul) mid = DLB_VFADD(lmul)(t3, ve, vl); \
            DLB_F32_T(lmul) u0 = DLB_VFMUL(lmul)(mid, vx, vl); \
            DLB_F32_T(lmul) u1 = DLB_VFADD(lmul)(u0, pre0, vl); \
            DLB_F32_T(lmul) u2 = DLB_VFSUB(lmul)(u1, pre1, vl); \
            DLB_F32_T(lmul) u3 = DLB_VFMACC_VF(lmul)(u2, 0.25f, mid, vl); \
            DLB_F32_T(lmul) out = DLB_VFADD(lmul)(u3, pre0, vl); \
            DLB_VSE32(lmul)(&b[offset], out, vl); \
            remaining -= (int)vl; \
            offset += (int)vl; \
        } \
    } \
} while (0)

#define WB11_ISLAND_M2(big_out, k, avl, chunk, lhs_big, rhs_big, acc_big, aux_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m2((avl) - start); \
        vfloat32m2_t lhs = __riscv_vget_v_f32m4_f32m2((lhs_big), (k)); \
        vfloat32m2_t rhs = __riscv_vget_v_f32m4_f32m2((rhs_big), (k)); \
        vfloat32m2_t acc = __riscv_vget_v_f32m4_f32m2((acc_big), (k)); \
        vfloat32m2_t aux = __riscv_vget_v_f32m4_f32m2((aux_big), (k)); \
        vfloat32m2_t t0 = __riscv_vfsub_vv_f32m2(lhs, aux, vlc); \
        vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(t0, rhs, vlc); \
        vfloat32m2_t t2 = __riscv_vfadd_vv_f32m2(t1, acc, vlc); \
        vfloat32m2_t t3 = __riscv_vfmacc_vf_f32m2(t2, 0.5f, rhs, vlc); \
        big_out = __riscv_vset_v_f32m2_f32m4((big_out), (k), t3); \
    } \
} while (0)

#define WB11_ISLAND_M1(big_out, k, avl, chunk, lhs_big, rhs_big, acc_big, aux_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m1((avl) - start); \
        vfloat32m1_t lhs = __riscv_vget_v_f32m4_f32m1((lhs_big), (k)); \
        vfloat32m1_t rhs = __riscv_vget_v_f32m4_f32m1((rhs_big), (k)); \
        vfloat32m1_t acc = __riscv_vget_v_f32m4_f32m1((acc_big), (k)); \
        vfloat32m1_t aux = __riscv_vget_v_f32m4_f32m1((aux_big), (k)); \
        vfloat32m1_t t0 = __riscv_vfsub_vv_f32m1(lhs, aux, vlc); \
        vfloat32m1_t t1 = __riscv_vfmul_vv_f32m1(t0, rhs, vlc); \
        vfloat32m1_t t2 = __riscv_vfadd_vv_f32m1(t1, acc, vlc); \
        vfloat32m1_t t3 = __riscv_vfmacc_vf_f32m1(t2, 0.5f, rhs, vlc); \
        big_out = __riscv_vset_v_f32m1_f32m4((big_out), (k), t3); \
    } \
} while (0)

static void run_dyn_main(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB11_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB11_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB11_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB11_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t pre0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t pre1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t mid = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);

            WB11_ISLAND_M2(mid, 0, avl, chunk, pre0, vc, pre1, vx);
            WB11_ISLAND_M2(mid, 1, avl, chunk, pre0, vc, pre1, vx);

            __riscv_vsetvl_e32m4(avl);
            mid = __riscv_vfadd_vv_f32m4(mid, ve, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            chunk = __riscv_vsetvl_e32m2(avl);

            WB11_ISLAND_M2(out, 0, avl, chunk, mid, vx, pre0, pre1);
            WB11_ISLAND_M2(out, 1, avl, chunk, mid, vx, pre0, pre1);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, pre0, avl);
            __riscv_vse32_v_f32m4(&b[offset], out, avl);
        }
    }
}

static void run_dyn_safe(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB11_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB11_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB11_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB11_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t pre0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t pre1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t mid = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m1(avl);

            WB11_ISLAND_M1(mid, 0, avl, chunk, pre0, vc, pre1, vx);
            WB11_ISLAND_M1(mid, 1, avl, chunk, pre0, vc, pre1, vx);
            WB11_ISLAND_M1(mid, 2, avl, chunk, pre0, vc, pre1, vx);
            WB11_ISLAND_M1(mid, 3, avl, chunk, pre0, vc, pre1, vx);

            __riscv_vsetvl_e32m4(avl);
            mid = __riscv_vfadd_vv_f32m4(mid, ve, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            chunk = __riscv_vsetvl_e32m1(avl);

            WB11_ISLAND_M1(out, 0, avl, chunk, mid, vx, pre0, pre1);
            WB11_ISLAND_M1(out, 1, avl, chunk, mid, vx, pre0, pre1);
            WB11_ISLAND_M1(out, 2, avl, chunk, mid, vx, pre0, pre1);
            WB11_ISLAND_M1(out, 3, avl, chunk, mid, vx, pre0, pre1);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, pre0, avl);
            __riscv_vse32_v_f32m4(&b[offset], out, avl);
        }
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    WB11_RUN_FIXED(m1);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    WB11_RUN_FIXED(m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    WB11_RUN_FIXED(m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_DYN_SAFE
    run_dyn_safe();
#else
    run_dyn_main();
#endif
}
