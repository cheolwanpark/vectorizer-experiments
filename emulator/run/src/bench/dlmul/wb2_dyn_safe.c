#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb2_activation[LEN_1D];
static int16_t wb2_weight[LEN_1D];
static int16_t wb2_bias16[LEN_1D];

#define GET_I16(big, k) __riscv_vget_v_i16m4_i16m1((big), (k))
#define SET_I32(big, k, small) __riscv_vset_v_i32m2_i32m8((big), (k), (small))

void kernel(void) {
    size_t vl4 = __riscv_vsetvl_e16m4((size_t)192);

    dlb_init_int16_triplet(wb2_activation, wb2_weight, wb2_bias16, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        for (int offset = 0; offset < 192; offset += (int)vl4) {
            size_t avl = (size_t)(192 - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vint16m4_t act_big = __riscv_vle16_v_i16m4(&wb2_activation[offset], avl);
            vint16m4_t wt_big = __riscv_vle16_v_i16m4(&wb2_weight[offset], avl);
            vint16m4_t bias_big = __riscv_vle16_v_i16m4(&wb2_bias16[offset], avl);
            vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, avl);
            size_t chunk = __riscv_vsetvl_e16m1(avl);

            {
                size_t start = (size_t)0 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m1(avl - start);
                    vint16m1_t act = GET_I16(act_big, 0);
                    vint16m1_t wt = GET_I16(wt_big, 0);
                    vint16m1_t bias = GET_I16(bias_big, 0);
                    vint32m2_t partial = __riscv_vwadd_vv_i32m2(act, wt, vlc);
                    vint32m2_t out = __riscv_vadd_vv_i32m2(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, wt, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, bias, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(wt, bias, vlc), vlc);
                    out_big = SET_I32(out_big, 0, out);
                }
            }
            {
                size_t start = (size_t)1 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m1(avl - start);
                    vint16m1_t act = GET_I16(act_big, 1);
                    vint16m1_t wt = GET_I16(wt_big, 1);
                    vint16m1_t bias = GET_I16(bias_big, 1);
                    vint32m2_t partial = __riscv_vwadd_vv_i32m2(act, wt, vlc);
                    vint32m2_t out = __riscv_vadd_vv_i32m2(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, wt, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, bias, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(wt, bias, vlc), vlc);
                    out_big = SET_I32(out_big, 1, out);
                }
            }
            {
                size_t start = (size_t)2 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m1(avl - start);
                    vint16m1_t act = GET_I16(act_big, 2);
                    vint16m1_t wt = GET_I16(wt_big, 2);
                    vint16m1_t bias = GET_I16(bias_big, 2);
                    vint32m2_t partial = __riscv_vwadd_vv_i32m2(act, wt, vlc);
                    vint32m2_t out = __riscv_vadd_vv_i32m2(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, wt, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, bias, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(wt, bias, vlc), vlc);
                    out_big = SET_I32(out_big, 2, out);
                }
            }
            {
                size_t start = (size_t)3 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m1(avl - start);
                    vint16m1_t act = GET_I16(act_big, 3);
                    vint16m1_t wt = GET_I16(wt_big, 3);
                    vint16m1_t bias = GET_I16(bias_big, 3);
                    vint32m2_t partial = __riscv_vwadd_vv_i32m2(act, wt, vlc);
                    vint32m2_t out = __riscv_vadd_vv_i32m2(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, wt, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(act, bias, vlc), vlc);
                    out = __riscv_vadd_vv_i32m2(out, __riscv_vwmul_vv_i32m2(wt, bias, vlc), vlc);
                    out_big = SET_I32(out_big, 3, out);
                }
            }

            __riscv_vsetvl_e32m8(avl);
            __riscv_vse32_v_i32m8(&indx[offset], out_big, avl);
        }
    }
}
