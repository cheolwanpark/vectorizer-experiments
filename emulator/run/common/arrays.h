#ifndef TSVC_ARRAYS_H
#define TSVC_ARRAYS_H

#include "types.h"

#define ARRAY_ALIGNMENT 64

extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t a[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t b[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t c[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t d[LEN_1D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t e[LEN_1D];

extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t aa[LEN_2D][LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t bb[LEN_2D][LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t cc[LEN_2D][LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t tt[LEN_2D][LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t flat_2d_array[LEN_2D * LEN_2D];
extern __attribute__((aligned(ARRAY_ALIGNMENT))) real_t x[LEN_1D];

extern __attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];
extern real_t * __restrict__ xx;
extern real_t *yy;

void init_arrays(void);

#endif
