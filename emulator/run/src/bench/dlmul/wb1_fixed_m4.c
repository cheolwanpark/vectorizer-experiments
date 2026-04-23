#include "dlmul_bench_common.h"
#include <riscv_vector.h>

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < 32; ++iter) {
        int offset = 0;
        int remaining = 192;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e32m4((size_t)remaining);
            vfloat32m4_t va = __riscv_vle32_v_f32m4(&a[offset], vl);
            vfloat32m4_t vb = __riscv_vle32_v_f32m4(&b[offset], vl);
            vfloat32m4_t vc = __riscv_vle32_v_f32m4(&c[offset], vl);
            vfloat32m4_t vx = __riscv_vle32_v_f32m4(&x[offset], vl);
            vfloat32m4_t sum = __riscv_vfadd_vv_f32m4(va, vb, vl);
            vfloat32m4_t mix = __riscv_vfmul_vv_f32m4(va, vc, vl);
            vfloat32m4_t centered = __riscv_vfsub_vv_f32m4(sum, vx, vl);
            vfloat32m4_t scaled = __riscv_vfmul_vv_f32m4(centered, vc, vl);
            vfloat32m4_t fused = __riscv_vfadd_vv_f32m4(scaled, mix, vl);
            fused = __riscv_vfadd_vv_f32m4(fused, sum, vl);
            vfloat32m4_t out = __riscv_vfmacc_vf_f32m4(vb, 0.5f, fused, vl);
            __riscv_vse32_v_f32m4(&a[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
