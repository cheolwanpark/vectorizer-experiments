#include "dlmul_bench_common.h"
#include <riscv_vector.h>

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < 28; ++iter) {
        int offset = 0;
        int remaining = 192;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e32m2((size_t)remaining);
            vfloat32m2_t va = __riscv_vle32_v_f32m2(&a[offset], vl);
            vfloat32m2_t vb = __riscv_vle32_v_f32m2(&b[offset], vl);
            vfloat32m2_t vc = __riscv_vle32_v_f32m2(&c[offset], vl);
            vfloat32m2_t vd = __riscv_vle32_v_f32m2(&d[offset], vl);
            vfloat32m2_t ve = __riscv_vle32_v_f32m2(&e[offset], vl);
            vfloat32m2_t vx = __riscv_vle32_v_f32m2(&x[offset], vl);
            vfloat32m2_t out = __riscv_vfadd_vv_f32m2(va, vb, vl);
            out = __riscv_vfadd_vv_f32m2(out, va, vl);
            out = __riscv_vfadd_vv_f32m2(out, vb, vl);
            out = __riscv_vfadd_vv_f32m2(out, vc, vl);
            out = __riscv_vfadd_vv_f32m2(out, vd, vl);
            out = __riscv_vfadd_vv_f32m2(out, ve, vl);
            out = __riscv_vfadd_vv_f32m2(out, vx, vl);
            out = __riscv_vfadd_vv_f32m2(out, vb, vl);
            __riscv_vse32_v_f32m2(&a[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
