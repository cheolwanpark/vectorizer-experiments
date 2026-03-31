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

extern __attribute__((aligned(ARRAY_ALIGNMENT))) int indx[LEN_1D];

void init_arrays(void);

#endif
