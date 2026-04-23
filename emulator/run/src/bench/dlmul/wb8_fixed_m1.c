#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb8_src0[LEN_1D];
static int16_t wb8_src1[LEN_1D];
static int16_t wb8_src2[LEN_1D];

void kernel(void) {
    dlb_init_int16_triplet(wb8_src0, wb8_src1, wb8_src2, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        int offset = 0;
        int remaining = 160;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e16m1((size_t)remaining);
            vint16m1_t x = __riscv_vle16_v_i16m1(&wb8_src0[offset], vl);
            vint16m1_t y = __riscv_vle16_v_i16m1(&wb8_src1[offset], vl);
            vint16m1_t z = __riscv_vle16_v_i16m1(&wb8_src2[offset], vl);
            vint32m2_t seed = __riscv_vwadd_vv_i32m2(x, y, vl);
            vint32m2_t out = __riscv_vadd_vv_i32m2(seed, seed, vl);
            out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(x, y, vl), vl);
            out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(x, z, vl), vl);
            out = __riscv_vadd_vv_i32m2(out, __riscv_vwadd_vv_i32m2(y, z, vl), vl);
            out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(y, y, vl), vl);
            __riscv_vse32_v_i32m2(&indx[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
