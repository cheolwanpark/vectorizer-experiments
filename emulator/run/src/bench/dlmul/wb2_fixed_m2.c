#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb2_activation[LEN_1D];
static int16_t wb2_weight[LEN_1D];
static int16_t wb2_bias16[LEN_1D];

void kernel(void) {
    dlb_init_int16_triplet(wb2_activation, wb2_weight, wb2_bias16, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        int offset = 0;
        int remaining = 192;
        while (remaining > 0) {
            size_t vl = __riscv_vsetvl_e16m2((size_t)remaining);
            vint16m2_t act = __riscv_vle16_v_i16m2(&wb2_activation[offset], vl);
            vint16m2_t wt = __riscv_vle16_v_i16m2(&wb2_weight[offset], vl);
            vint16m2_t bias = __riscv_vle16_v_i16m2(&wb2_bias16[offset], vl);
            vint32m4_t partial = __riscv_vwadd_vv_i32m4(act, wt, vl);
            vint32m4_t out = __riscv_vadd_vv_i32m4(partial, partial, vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(act, wt, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(act, bias, vl), vl);
            out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(wt, bias, vl), vl);
            __riscv_vse32_v_i32m4(&indx[offset], out, vl);
            remaining -= (int)vl;
            offset += (int)vl;
        }
    }
}
