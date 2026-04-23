#include "dlmul_bench_common.h"
#include "dlmul_bench_vector_macros.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_MAIN
#endif

#define WB13_TOTAL_ELEMS 256
#define WB13_OUTER_ITERS 22

#define WB13_RUN_FIXED(lmul) do { \
    dlb_init_real_inputs(); \
    for (int iter = 0; iter < WB13_OUTER_ITERS; ++iter) { \
        int offset = 0; \
        int remaining = WB13_TOTAL_ELEMS; \
        while (remaining > 0) { \
            size_t vl = DLB_VSETVL_E32(lmul)((size_t)remaining); \
            DLB_F32_T(lmul) va = DLB_VLE32(lmul)(&a[offset], vl); \
            DLB_F32_T(lmul) vb = DLB_VLE32(lmul)(&b[offset], vl); \
            DLB_F32_T(lmul) vc = DLB_VLE32(lmul)(&c[offset], vl); \
            DLB_F32_T(lmul) vd = DLB_VLE32(lmul)(&d[offset], vl); \
            DLB_F32_T(lmul) ve = DLB_VLE32(lmul)(&e[offset], vl); \
            DLB_F32_T(lmul) vx = DLB_VLE32(lmul)(&x[offset], vl); \
            DLB_F32_T(lmul) base = DLB_VFADD(lmul)(va, vb, vl); \
            DLB_F32_T(lmul) gate = DLB_VFMUL(lmul)(vc, vd, vl); \
            DLB_F32_T(lmul) t0 = DLB_VFADD(lmul)(base, gate, vl); \
            DLB_F32_T(lmul) t1 = DLB_VFMUL(lmul)(t0, vx, vl); \
            DLB_F32_T(lmul) t2 = DLB_VFSUB(lmul)(t1, ve, vl); \
            DLB_F32_T(lmul) t3 = DLB_VFMACC_VF(lmul)(t2, 0.375f, gate, vl); \
            DLB_F32_T(lmul) t4 = DLB_VFADD(lmul)(t3, t0, vl); \
            DLB_F32_T(lmul) t5 = DLB_VFMUL(lmul)(t4, base, vl); \
            DLB_F32_T(lmul) out = DLB_VFADD(lmul)(t5, gate, vl); \
            out = DLB_VFMACC_VF(lmul)(out, 0.125f, ve, vl); \
            out = DLB_VFADD(lmul)(out, vx, vl); \
            DLB_VSE32(lmul)(&d[offset], out, vl); \
            remaining -= (int)vl; \
            offset += (int)vl; \
        } \
    } \
} while (0)

#define WB13_ISLAND_M2(big_out, k, avl, chunk, base_big, gate_big, ve_big, vx_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m2((avl) - start); \
        vfloat32m2_t base_part = __riscv_vget_v_f32m4_f32m2((base_big), (k)); \
        vfloat32m2_t gate_part = __riscv_vget_v_f32m4_f32m2((gate_big), (k)); \
        vfloat32m2_t ve_part = __riscv_vget_v_f32m4_f32m2((ve_big), (k)); \
        vfloat32m2_t vx_part = __riscv_vget_v_f32m4_f32m2((vx_big), (k)); \
        vfloat32m2_t t0 = __riscv_vfadd_vv_f32m2(base_part, gate_part, vlc); \
        vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(t0, vx_part, vlc); \
        vfloat32m2_t t2 = __riscv_vfsub_vv_f32m2(t1, ve_part, vlc); \
        vfloat32m2_t t3 = __riscv_vfmacc_vf_f32m2(t2, 0.375f, gate_part, vlc); \
        vfloat32m2_t t4 = __riscv_vfadd_vv_f32m2(t3, t0, vlc); \
        vfloat32m2_t out_part = __riscv_vfmul_vv_f32m2(t4, base_part, vlc); \
        big_out = __riscv_vset_v_f32m2_f32m4((big_out), (k), out_part); \
    } \
} while (0)

#define WB13_ISLAND_M1(big_out, k, avl, chunk, base_big, gate_big, ve_big, vx_big) do { \
    size_t start = (size_t)(k) * (chunk); \
    if (start < (avl)) { \
        size_t vlc = __riscv_vsetvl_e32m1((avl) - start); \
        vfloat32m1_t base_part = __riscv_vget_v_f32m4_f32m1((base_big), (k)); \
        vfloat32m1_t gate_part = __riscv_vget_v_f32m4_f32m1((gate_big), (k)); \
        vfloat32m1_t ve_part = __riscv_vget_v_f32m4_f32m1((ve_big), (k)); \
        vfloat32m1_t vx_part = __riscv_vget_v_f32m4_f32m1((vx_big), (k)); \
        vfloat32m1_t t0 = __riscv_vfadd_vv_f32m1(base_part, gate_part, vlc); \
        vfloat32m1_t t1 = __riscv_vfmul_vv_f32m1(t0, vx_part, vlc); \
        vfloat32m1_t t2 = __riscv_vfsub_vv_f32m1(t1, ve_part, vlc); \
        vfloat32m1_t t3 = __riscv_vfmacc_vf_f32m1(t2, 0.375f, gate_part, vlc); \
        vfloat32m1_t t4 = __riscv_vfadd_vv_f32m1(t3, t0, vlc); \
        vfloat32m1_t out_part = __riscv_vfmul_vv_f32m1(t4, base_part, vlc); \
        big_out = __riscv_vset_v_f32m1_f32m4((big_out), (k), out_part); \
    } \
} while (0)

static void run_dyn_main(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB13_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB13_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB13_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB13_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t base = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t gate = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);

            WB13_ISLAND_M2(out, 0, avl, chunk, base, gate, ve, vx);
            WB13_ISLAND_M2(out, 1, avl, chunk, base, gate, ve, vx);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, gate, avl);
            out = __riscv_vfmacc_vf_f32m4(out, 0.125f, ve, avl);
            out = __riscv_vfadd_vv_f32m4(out, vx, avl);
            __riscv_vse32_v_f32m4(&d[offset], out, avl);
        }
    }
}

static void run_dyn_safe(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)WB13_TOTAL_ELEMS);

    dlb_init_real_inputs();
    for (int iter = 0; iter < WB13_OUTER_ITERS; ++iter) {
        for (int offset = 0; offset < WB13_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(WB13_TOTAL_ELEMS - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t base = __riscv_vfadd_vv_f32m4(va, vb, avl);
            vfloat32m4_t gate = __riscv_vfmul_vv_f32m4(vc, vd, avl);
            vfloat32m4_t out = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m1(avl);

            WB13_ISLAND_M1(out, 0, avl, chunk, base, gate, ve, vx);
            WB13_ISLAND_M1(out, 1, avl, chunk, base, gate, ve, vx);
            WB13_ISLAND_M1(out, 2, avl, chunk, base, gate, ve, vx);
            WB13_ISLAND_M1(out, 3, avl, chunk, base, gate, ve, vx);

            __riscv_vsetvl_e32m4(avl);
            out = __riscv_vfadd_vv_f32m4(out, gate, avl);
            out = __riscv_vfmacc_vf_f32m4(out, 0.125f, ve, avl);
            out = __riscv_vfadd_vv_f32m4(out, vx, avl);
            __riscv_vse32_v_f32m4(&d[offset], out, avl);
        }
    }
}

void kernel(void) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
    WB13_RUN_FIXED(m1);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
    WB13_RUN_FIXED(m2);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
    WB13_RUN_FIXED(m4);
#elif DLB_BENCH_VARIANT == DLB_VARIANT_DYN_SAFE
    run_dyn_safe();
#else
    run_dyn_main();
#endif
}
