#include "dlmul_bench_common.h"
#include <riscv_vector.h>

void kernel(void) {
    dlb_init_real_inputs();
    for (int iter = 0; iter < 32; ++iter) {
        int offset = 0;
        int remaining = 192;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e32m1((size_t)remaining);
            vfloat32m1_t va = __riscv_vle32_v_f32m1(&a[offset], vl);
            vfloat32m1_t vb = __riscv_vle32_v_f32m1(&b[offset], vl);
            vfloat32m1_t vc = __riscv_vle32_v_f32m1(&c[offset], vl);
            vfloat32m1_t vx = __riscv_vle32_v_f32m1(&x[offset], vl);
            vfloat32m1_t sum = __riscv_vfadd_vv_f32m1(va, vb, vl);
            vfloat32m1_t mix = __riscv_vfmul_vv_f32m1(va, vc, vl);
            vfloat32m1_t centered = __riscv_vfsub_vv_f32m1(sum, vx, vl);
            vfloat32m1_t scaled = __riscv_vfmul_vv_f32m1(centered, vc, vl);
            vfloat32m1_t fused = __riscv_vfadd_vv_f32m1(scaled, mix, vl);
            fused = __riscv_vfadd_vv_f32m1(fused, sum, vl);
            vfloat32m1_t out = __riscv_vfmacc_vf_f32m1(vb, 0.5f, fused, vl);
            __riscv_vse32_v_f32m1(&a[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
