#include "dlmul_bench_common.h"
#include <riscv_vector.h>

#define GET(big, k) __riscv_vget_v_f32m4_f32m2((big), (k))
#define SET(big, k, small) __riscv_vset_v_f32m2_f32m4((big), (k), (small))

void kernel(void) {
    size_t vl4 = __riscv_vsetvl_e32m4((size_t)192);

    dlb_init_real_inputs();
    for (int iter = 0; iter < 28; ++iter) {
        for (int offset = 0; offset < 192; offset += (int)vl4) {
            size_t avl = (size_t)(192 - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], avl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], avl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], avl);
            vfloat32m4_t vd = __riscv_vle32_v_f32m4(&d[offset], avl);
            vfloat32m4_t ve = __riscv_vle32_v_f32m4(&e[offset], avl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], avl);
            vfloat32m4_t out_big = __riscv_vfmv_v_f_f32m4(0.0f, avl);
            size_t chunk = __riscv_vsetvl_e32m2(avl);

            {
                size_t start = (size_t)0 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e32m2(avl - start);
                    vfloat32m2_t xa = GET(va, 0);
                    vfloat32m2_t xb = GET(vb, 0);
                    vfloat32m2_t xc = GET(vc, 0);
                    vfloat32m2_t xd = GET(vd, 0);
                    vfloat32m2_t xe = GET(ve, 0);
                    vfloat32m2_t xx = GET(vx, 0);
                    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(xa, xb, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xa, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xb, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xc, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xd, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xe, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xx, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xb, vlc);
                    out_big = SET(out_big, 0, out);
                }
            }
            {
                size_t start = (size_t)1 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e32m2(avl - start);
                    vfloat32m2_t xa = GET(va, 1);
                    vfloat32m2_t xb = GET(vb, 1);
                    vfloat32m2_t xc = GET(vc, 1);
                    vfloat32m2_t xd = GET(vd, 1);
                    vfloat32m2_t xe = GET(ve, 1);
                    vfloat32m2_t xx = GET(vx, 1);
                    vfloat32m2_t out = __riscv_vfadd_vv_f32m2(xa, xb, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xa, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xb, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xc, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xd, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xe, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xx, vlc);
                    out = __riscv_vfadd_vv_f32m2(out, xb, vlc);
                    out_big = SET(out_big, 1, out);
                }
            }

            __riscv_vsetvl_e32m4(avl);
            __riscv_vse32_v_f32m4(&a[offset], out_big, avl);
        }
    }
}
