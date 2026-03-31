#include "arrays.h"

__attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t b[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t c[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t d[LEN_1D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t e[LEN_1D];

__attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t bb[LEN_2D][LEN_2D];
__attribute__((aligned(ARRAY_ALIGNMENT))) real_t cc[LEN_2D][LEN_2D];

__attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];

__attribute__((weak)) void init_arrays(void) {
    for (size_t i = 0; i < LEN_1D; i++) {
        a[i] = 0.0f;
        b[i] = (i % 2) ? 1.0f : -1.0f;
        c[i] = 1.0f;
        d[i] = 1.0f;
        e[i] = 1.0f;
        indx[i] = (int)(i % LEN_1D);
    }
    for (size_t i = 0; i < LEN_2D; i++) {
        for (size_t j = 0; j < LEN_2D; j++) {
            aa[i][j] = 0.0f;
            bb[i][j] = 1.0f;
            cc[i][j] = 1.0f;
        }
    }
}
