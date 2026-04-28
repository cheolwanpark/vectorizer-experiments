#ifndef DLMUL_BENCH_COMMON_H
#define DLMUL_BENCH_COMMON_H

#include "common.h"
#include <stdint.h>

#define DLB_VARIANT_FIXED_M1 1
#define DLB_VARIANT_FIXED_M2 2
#define DLB_VARIANT_FIXED_M4 4
#define DLB_VARIANT_FIXED_M8 8
#define DLB_VARIANT_DYN_M4_M2_M4 42
#define DLB_VARIANT_DYN_M8_M2_M8 82
#define DLB_VARIANT_DYN_M8_M2_M2 822
#define DLB_VARIANT_DYN_M8_M2_M4 824

static inline void dlb_init_real_inputs(void) {
    for (int i = 0; i < LEN_1D; ++i) {
        a[i] = (real_t)((i % 17) * 0.125f + 0.5f);
        b[i] = (real_t)((i % 13) * 0.25f + 1.0f);
        c[i] = (real_t)((i % 11) * 0.5f + 0.75f);
        d[i] = (real_t)((i % 7) * 0.375f + 0.25f);
        e[i] = (real_t)((i % 5) * 0.625f + 0.5f);
        x[i] = (real_t)((i % 19) * 0.1875f + 0.125f);
        flat_2d_array[i] = (real_t)((i % 23) * 0.0625f + 0.25f);
    }

    for (int row = 0; row < LEN_2D; ++row) {
        for (int col = 0; col < LEN_2D; ++col) {
            aa[row][col] = (real_t)(((row * 5 + col) % 29) * 0.0625f + 0.5f);
            bb[row][col] = (real_t)(((row * 7 + col) % 31) * 0.03125f + 0.25f);
            cc[row][col] = (real_t)(((row * 3 + col) % 17) * 0.09375f + 0.125f);
            tt[row][col] = (real_t)(((row * 11 + col) % 19) * 0.046875f + 0.375f);
        }
    }
}

static inline void dlb_init_int16_triplet(
    int16_t *lhs,
    int16_t *rhs,
    int16_t *bias,
    int total
) {
    for (int i = 0; i < total; ++i) {
        lhs[i] = (int16_t)((i % 31) - 15);
        rhs[i] = (int16_t)(((i * 3) % 27) - 13);
        bias[i] = (int16_t)(((i * 5) % 21) - 10);
    }
}

#endif
