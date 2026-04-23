#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];

void kernel(void) {
    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        int offset = 0;
        int remaining = 128;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e16m2((size_t)remaining);
            vint16m2_t x = __riscv_vle16_v_i16m2(&wb5_src0[offset], vl);
            vint16m2_t y = __riscv_vle16_v_i16m2(&wb5_src1[offset], vl);
            vint16m2_t z = __riscv_vle16_v_i16m2(&wb5_src2[offset], vl);
            vint32m4_t partial = __riscv_vwadd_vv_i32m4(x, y, vl);
            vint32m4_t out = __riscv_vadd_vv_i32m4(partial, partial, vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, y, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, y, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, z, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, z, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, z, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, z, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, x, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, y, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, z, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, x, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(z, x, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, y, vl), vl);
            __riscv_vse32_v_i32m4(&indx[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
