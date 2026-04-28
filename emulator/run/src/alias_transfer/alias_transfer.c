#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#ifndef DLB_BENCH_VARIANT
#define DLB_BENCH_VARIANT DLB_VARIANT_DYN_M4_M2_M4
#endif

#ifndef DLB_ALIAS_MODE
#define DLB_ALIAS_MODE 0
#endif

#define DLB_ALIAS_OK 0
#define DLB_ALIAS_BAD 1

#define ALIAS_TOTAL_ELEMS 192
#define ALIAS_OUTER_ITERS 40

void kernel(void) {
    dlb_init_real_inputs();

    for (int iter = 0; iter < ALIAS_OUTER_ITERS; ++iter) {
#if DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M1
        size_t vl_base = __riscv_vsetvl_e32m1((size_t)ALIAS_TOTAL_ELEMS);
        for (int offset = 0; offset < ALIAS_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(ALIAS_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], avl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], avl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], avl);
            vfloat32m1_t aux = __riscv_vle32_v_f32m1(&d[offset], avl);
            vfloat32m1_t phase1 = __riscv_vfadd_vv_f32m1(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m1(phase1, 0.25f, vc, avl);

#if DLB_ALIAS_MODE == DLB_ALIAS_OK
            phase1 = __riscv_vfadd_vv_f32m1(phase1, phase1, avl);
            __riscv_vse32_v_f32m1(&a[offset], phase1, avl);
#else
            vfloat32m1_t t0 = __riscv_vfadd_vv_f32m1(phase1, phase1, avl);
            vfloat32m1_t t1 = __riscv_vfmul_vv_f32m1(phase1, phase1, avl);
            vfloat32m1_t t2 = __riscv_vfmacc_vf_f32m1(aux, 0.125f, phase1, avl);
            vfloat32m1_t orig = __riscv_vfmul_vv_f32m1(phase1, phase1, avl);
            orig = __riscv_vfmacc_vf_f32m1(orig, 0.0625f, aux, avl);

            __riscv_vse32_v_f32m1(&a[offset], orig, avl);
            __riscv_vse32_v_f32m1(&b[offset], t0, avl);
            __riscv_vse32_v_f32m1(&c[offset], t1, avl);
            __riscv_vse32_v_f32m1(&d[offset], t2, avl);
#endif
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M2
        size_t vl_base = __riscv_vsetvl_e32m2((size_t)ALIAS_TOTAL_ELEMS);
        for (int offset = 0; offset < ALIAS_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(ALIAS_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], avl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], avl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], avl);
            vfloat32m2_t aux = __riscv_vle32_v_f32m2(&d[offset], avl);
            vfloat32m2_t phase1 = __riscv_vfadd_vv_f32m2(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m2(phase1, 0.25f, vc, avl);

#if DLB_ALIAS_MODE == DLB_ALIAS_OK
            phase1 = __riscv_vfadd_vv_f32m2(phase1, phase1, avl);
            __riscv_vse32_v_f32m2(&a[offset], phase1, avl);
#else
            vfloat32m2_t t0 = __riscv_vfadd_vv_f32m2(phase1, phase1, avl);
            vfloat32m2_t t1 = __riscv_vfmul_vv_f32m2(phase1, phase1, avl);
            vfloat32m2_t t2 = __riscv_vfmacc_vf_f32m2(aux, 0.125f, phase1, avl);
            vfloat32m2_t orig = __riscv_vfmul_vv_f32m2(phase1, phase1, avl);
            orig = __riscv_vfmacc_vf_f32m2(orig, 0.0625f, aux, avl);

            __riscv_vse32_v_f32m2(&a[offset], orig, avl);
            __riscv_vse32_v_f32m2(&b[offset], t0, avl);
            __riscv_vse32_v_f32m2(&c[offset], t1, avl);
            __riscv_vse32_v_f32m2(&d[offset], t2, avl);
#endif
        }
#elif DLB_BENCH_VARIANT == DLB_VARIANT_FIXED_M4
        size_t vl_base = __riscv_vsetvl_e32m4((size_t)ALIAS_TOTAL_ELEMS);
        for (int offset = 0; offset < ALIAS_TOTAL_ELEMS; offset += (int)vl_base) {
            size_t avl = (size_t)(ALIAS_TOTAL_ELEMS - offset);
            if (avl > vl_base) avl = vl_base;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t aux = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t phase1 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m4(phase1, 0.25f, vc, avl);

#if DLB_ALIAS_MODE == DLB_ALIAS_OK
            phase1 = __riscv_vfadd_vv_f32m4(phase1, phase1, avl);
            __riscv_vse32_v_f32m4(&a[offset], phase1, avl);
#else
            vfloat32m4_t t0 = __riscv_vfadd_vv_f32m4(phase1, phase1, avl);
            vfloat32m4_t t1 = __riscv_vfmul_vv_f32m4(phase1, phase1, avl);
            vfloat32m4_t t2 = __riscv_vfmacc_vf_f32m4(aux, 0.125f, phase1, avl);
            vfloat32m4_t orig = __riscv_vfmul_vv_f32m4(phase1, phase1, avl);
            orig = __riscv_vfmacc_vf_f32m4(orig, 0.0625f, aux, avl);

            __riscv_vse32_v_f32m4(&a[offset], orig, avl);
            __riscv_vse32_v_f32m4(&b[offset], t0, avl);
            __riscv_vse32_v_f32m4(&c[offset], t1, avl);
            __riscv_vse32_v_f32m4(&d[offset], t2, avl);
#endif
        }
#else
        size_t vl4 = __riscv_vsetvl_e32m4((size_t)ALIAS_TOTAL_ELEMS);
        for (int offset = 0; offset < ALIAS_TOTAL_ELEMS; offset += (int)vl4) {
            size_t avl = (size_t)(ALIAS_TOTAL_ELEMS - offset);
            if (avl > vl4) avl = vl4;

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t aux = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t phase1 = __riscv_vfadd_vv_f32m4(va, vb, avl);
            phase1 = __riscv_vfmacc_vf_f32m4(phase1, 0.25f, vc, avl);

#if DLB_ALIAS_MODE == DLB_ALIAS_OK
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define ALIAS_OK_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t part = __riscv_vget_v_f32m4_f32m2(phase1, (K)); \
        part = __riscv_vfadd_vv_f32m2(part, part, vlc); \
        phase1 = __riscv_vset_v_f32m2_f32m4(phase1, (K), part); \
    } \
} while (0)
            ALIAS_OK_CHUNK(0);
            ALIAS_OK_CHUNK(1);
#undef ALIAS_OK_CHUNK
            __riscv_vsetvl_e32m4(avl);
            __riscv_vse32_v_f32m4(&a[offset], phase1, avl);
#else
            vfloat32m4_t t0 = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            vfloat32m4_t t1 = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            vfloat32m4_t t2 = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);
#define ALIAS_BAD_CHUNK(K) do { \
    size_t start = (size_t)(K) * chunk; \
    if (start < avl) { \
        size_t vlc = __riscv_vsetvl_e32m2(avl - start); \
        vfloat32m2_t xa = __riscv_vget_v_f32m4_f32m2(phase1, (K)); \
        vfloat32m2_t xaux = __riscv_vget_v_f32m4_f32m2(aux, (K)); \
        vfloat32m2_t out0 = __riscv_vfadd_vv_f32m2(xa, xa, vlc); \
        vfloat32m2_t out1 = __riscv_vfmul_vv_f32m2(xa, xa, vlc); \
        vfloat32m2_t out2 = __riscv_vfmacc_vf_f32m2(xaux, 0.125f, xa, vlc); \
        t0 = __riscv_vset_v_f32m2_f32m4(t0, (K), out0); \
        t1 = __riscv_vset_v_f32m2_f32m4(t1, (K), out1); \
        t2 = __riscv_vset_v_f32m2_f32m4(t2, (K), out2); \
    } \
} while (0)
            ALIAS_BAD_CHUNK(0);
            ALIAS_BAD_CHUNK(1);
#undef ALIAS_BAD_CHUNK
            __riscv_vsetvl_e32m4(avl);
            vfloat32m4_t orig = __riscv_vfmul_vv_f32m4(phase1, phase1, avl);
            orig = __riscv_vfmacc_vf_f32m4(orig, 0.0625f, aux, avl);

            __riscv_vse32_v_f32m4(&a[offset], orig, avl);
            __riscv_vse32_v_f32m4(&b[offset], t0, avl);
            __riscv_vse32_v_f32m4(&c[offset], t1, avl);
            __riscv_vse32_v_f32m4(&d[offset], t2, avl);
#endif
        }
#endif
    }
}
