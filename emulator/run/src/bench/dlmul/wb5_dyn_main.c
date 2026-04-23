#include "dlmul_bench_common.h"
#include <riscv_vector.h>

static int16_t wb5_src0[LEN_1D];
static int16_t wb5_src1[LEN_1D];
static int16_t wb5_src2[LEN_1D];

#define GET_I16(big, k) __riscv_vget_v_i16m4_i16m2((big), (k))
#define SET_I32(big, k, small) __riscv_vset_v_i32m4_i32m8((big), (k), (small))

void kernel(void) {
    size_t vl4 = __riscv_vsetvl_e16m4((size_t)128);

    dlb_init_int16_triplet(wb5_src0, wb5_src1, wb5_src2, LEN_1D);
    for (int iter = 0; iter < 24; ++iter) {
        for (int offset = 0; offset < 128; offset += (int)vl4) {
            size_t avl = (size_t)(128 - offset);
            if (avl > vl4) {
                avl = vl4;
            }

            vint16m4_t x_big = __riscv_vle16_v_i16m4(&wb5_src0[offset], avl);
            vint16m4_t y_big = __riscv_vle16_v_i16m4(&wb5_src1[offset], avl);
            vint16m4_t z_big = __riscv_vle16_v_i16m4(&wb5_src2[offset], avl);
            vint32m8_t out_big = __riscv_vmv_v_x_i32m8(0, avl);
            size_t chunk = __riscv_vsetvl_e16m2(avl);

            {
                size_t start = (size_t)0 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m2(avl - start);
                    vint16m2_t x = GET_I16(x_big, 0);
                    vint16m2_t y = GET_I16(y_big, 0);
                    vint16m2_t z = GET_I16(z_big, 0);
                    vint32m4_t partial = __riscv_vwadd_vv_i32m4(x, y, vlc);
                    vint32m4_t out = __riscv_vadd_vv_i32m4(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(z, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, y, vlc), vlc);
                    out_big = SET_I32(out_big, 0, out);
                }
            }
            {
                size_t start = (size_t)1 * chunk;
                if (start < avl) {
                    size_t vlc = __riscv_vsetvl_e16m2(avl - start);
                    vint16m2_t x = GET_I16(x_big, 1);
                    vint16m2_t y = GET_I16(y_big, 1);
                    vint16m2_t z = GET_I16(z_big, 1);
                    vint32m4_t partial = __riscv_vwadd_vv_i32m4(x, y, vlc);
                    vint32m4_t out = __riscv_vadd_vv_i32m4(partial, partial, vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(x, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(x, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(y, y, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, z, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(y, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwadd_vv_i32m4(z, x, vlc), vlc);
                    out = __riscv_vadd_vv_i32m4(out, __riscv_vwmul_vv_i32m4(z, y, vlc), vlc);
                    out_big = SET_I32(out_big, 1, out);
                }
            }

            __riscv_vsetvl_e32m8(avl);
            __riscv_vse32_v_i32m8(&indx[offset], out_big, avl);
        }
    }
}
