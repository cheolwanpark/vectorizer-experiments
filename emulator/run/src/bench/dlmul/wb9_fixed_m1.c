#include "dlmul_bench_common.h"
#include <riscv_vector.h>

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < 28; ++iter) {
        int offset = 0;
        int remaining = 192;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e32m1((size_t)remaining);
            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], vl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], vl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], vl);
            vfloat32m1_t vd = __riscv_vle32_v_f32m1(&d[offset], vl);
            vfloat32m1_t ve = __riscv_vle32_v_f32m1(&e[offset], vl);
            vfloat32m1_t vx = __riscv_vle32_v_f32m1(&x[offset], vl);
            vfloat32m1_t out = __riscv_vfadd_vv_f32m1(va, vb, vl);
            out = __riscv_vfadd_vv_f32m1(out, va, vl);
            out = __riscv_vfadd_vv_f32m1(out, vb, vl);
            out = __riscv_vfadd_vv_f32m1(out, vc, vl);
            out = __riscv_vfadd_vv_f32m1(out, vd, vl);
            out = __riscv_vfadd_vv_f32m1(out, ve, vl);
            out = __riscv_vfadd_vv_f32m1(out, vx, vl);
            out = __riscv_vfadd_vv_f32m1(out, vb, vl);
            __riscv_vse32_v_f32m1(&a[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
