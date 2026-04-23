#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_MAIN
#endif

#define WB12_TOTAL_ELEMS 224
#define WB12_OUTER_ITERS 24

#define WB12_RUN_FIXED(lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < WB12_OUTER_ITERS; ++iter) { \
        int offset = 0; \
        int remaining = WB12_TOTAL_ELEMS; \
        while (remaining > 0) { \
            size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
            DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
            DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
            DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
            DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
            DLB_F32_T(lmul) ve = DLB_VLE32(lmul)(&e[offset], vl); \
            DLB_F32_T(lmul) vx = DLB_VLE32(lmul)(&x[offset], vl); \
            DLB_F32_T(lmul) vf = DLB_VLE32(lmul)(&flat_2d_array[offset], vl); \
            DLB_F32_T(lmul) p0 = DLB_VFADD(lmul)(va, vb, vl); \
            DLB_F32_T(lmul) p1 = DLB_VFMUL(lmul)(vc, vd, vl); \
            DLB_F32_T(lmul) p2 = DLB_VFADD(lmul)(ve, vx, vl); \
            DLB_F32_T(lmul) p3 = DLB_VFSUB(lmul)(vf, va, vl); \
            DLB_F32_T(lmul) t0 = DLB_VFADD(lmul)(p0, p1, vl); \
            DLB_F32_T(lmul) t1 = DLB_VFMUL(lmul)(p2, p3, vl); \
            DLB_F32_T(lmul) t2 = DLB_VFMACC_VF(lmul)(t0, 0.25f, t1, vl); \
            DLB_F32_T(lmul) t3 = DLB_VFSUB(lmul)(t2, p1, vl); \
            DLB_F32_T(lmul) t4 = DLB_VFMUL(lmul)(t3, p0, vl); \
            DLB_F32_T(lmul) t5 = DLB_VFADD(lmul)(t4, p2, vl); \
            DLB_F32_T(lmul) t6 = DLB_VFMACC_VF(lmul)(t5, 0.125f, p3, vl); \
            DLB_F32_T(lmul) out = DLB_VFADD(lmul)(t6, p0, vl); \
            DLB_VSE32(lmul)(&c[offset], out, vl); \
            remaining -= (int)vl; \
            offset += (int)vl; \
        } \
    } \
} while (0)

#define WB12_ISLAND_M2(big_out, k, avl, chunk, p0_big, p1_big, p2_big, p3_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m2((avl) - start); \
        vfloat32m2_t p0 = __riscv_vget_v_f32m4_f32m2((p0_big), (k)); \
        vfloat32m2_t p1 = __riscv_vget_v_f32m4_f32m2((p1_big), (k)); \
        vfloat32m2_t p2 = __riscv_vget_v_f32m4_f32m2((p2_big), (k)); \
        vfloat32m2_t p3 = __riscv_vget_v_f32m4_f32m2((p3_big), (k)); \
        vfloat32m2_t t0 = __riscv_vfadd_vv_f32m2(p0, p1, vlc); \
        vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(p2, p3, vlc); \
        vfloat32m2_t t2 = __riscv_vfmacc_vf_f32m2(t0, 0.25f, t1, vlc); \
        vfloat32m2_t t3 = __riscv_vfsub_vv_f32m2(t2, p1, vlc); \
        vfloat32m2_t t4 = __riscv_vfmul_vv_f32m2(t3, p0, vlc); \
        vfloat32m2_t t5 = __riscv_vfadd_vv_f32m2(t4, p2, vlc); \
        vfloat32m2_t out = __riscv_vfmacc_vf_f32m2(t5, 0.125f, p3, vlc); \
        big_out = __riscv_vset_v_f32m2_f32m4((big_out), (k), out); \
    } \
} while (0)

#define WB12_ISLAND_M1(big_out, k, avl, chunk, p0_big, p1_big, p2_big, p3_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m1((avl) - start); \
        vfloat32m1_t p0 = __riscv_vget_v_f32m4_f32m1((p0_big), (k)); \
        vfloat32m1_t p1 = __riscv_vget_v_f32m4_f32m1((p1_big), (k)); \
        vfloat32m1_t p2 = __riscv_vget_v_f32m4_f32m1((p2_big), (k)); \
        vfloat32m1_t p3 = __riscv_vget_v_f32m4_f32m1((p3_big), (k)); \
        vfloat32m1_t t0 = __riscv_vfadd_vv_f32m1(p0, p1, vlc); \
        vfloat32m1_t t1 = __riscv_vfmul_vv_f32m1(p2, p3, vlc); \
        vfloat32m1_t t2 = __riscv_vfmacc_vf_f32m1(t0, 0.25f, t1, vlc); \
        vfloat32m1_t t3 = __riscv_vfsub_vv_f32m1(t2, p1, vlc); \
        vfloat32m1_t t4 = __riscv_vfmul_vv_f32m1(t3, p0, vlc); \
        vfloat32m1_t t5 = __riscv_vfadd_vv_f32m1(t4, p2, vlc); \
        vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(t5, 0.125f, p3, vlc); \
        big_out = __riscv_vset_v_f32m1_f32m4((big_out), (k), out); \
    } \
} while (0)

static void run_dyn_main(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB12_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB12_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB12_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB12_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t vf = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t p0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t p1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t p2 = __riscv_vfadd_vv_f32m4(ve, vx, avl);
            vfloat32m4_t p3 = __riscv_vfsub_vv_f32m4(vf, va, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);

            WB12_ISLAND_M2(out, 0, avl, chunk, p0, p1, p2, p3);
            WB12_ISLAND_M2(out, 1, avl, chunk, p0, p1, p2, p3);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, p0, avl);
            __riscv_vse32_v_f32m4(&c[offset], out, avl);
        }
    }
}

static void run_dyn_safe(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB12_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB12_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB12_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB12_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t vf = __riscv_vle32_v_f32m4(&flat_2d_array[offset], avl);
            vfloat32m4_t p0 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t p1 = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t p2 = __riscv_vfadd_vv_f32m4(ve, vx, avl);
            vfloat32m4_t p3 = __riscv_vfsub_vv_f32m4(vf, va, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m1(avl);

            WB12_ISLAND_M1(out, 0, avl, chunk, p0, p1, p2, p3);
            WB12_ISLAND_M1(out, 1, avl, chunk, p0, p1, p2, p3);
            WB12_ISLAND_M1(out, 2, avl, chunk, p0, p1, p2, p3);
            WB12_ISLAND_M1(out, 3, avl, chunk, p0, p1, p2, p3);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, p0, avl);
            __riscv_vse32_v_f32m4(&c[offset], out, avl);
        }
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    WB12_RUN_FIXED(m1);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    WB12_RUN_FIXED(m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    WB12_RUN_FIXED(m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_DYN_SAFE
    run_dyn_safe();
#else
    run_dyn_main();
#endif
}
