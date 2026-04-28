/* TSVC_EMULATE_GENERATED: s141 */
#include <math.h>
#include <stdlib.h>
#include "common.h"

#ifndef ABS
#define ABS fabsf
#endif

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;
extern real_t flat_2d_array[LEN_2D * LEN_2D];
extern real_t x[LEN_1D];
extern real_t tt[LEN_2D][LEN_2D];
extern real_t * __restrict__ xx;
extern real_t *yy;
extern real_t test(real_t *A);
extern real_t f(real_t a, real_t b);

void kernel(void) {
    //    nonlinear dependence testing
    //    walk a row in a symmetric packed array
    //    element a(i,j) for (int j>i) stored in location j*(j-1)/2+i


        int k;
    for (int i = 0; i < LEN_2D; i++) {
        k = (i+1) * ((i+1) - 1) / 2 + (i+1)-1;
        for (int j = i; j < LEN_2D; j++) {
            flat_2d_array[k] += bb[j][i];
            k += j+1;
        }
    }
}
