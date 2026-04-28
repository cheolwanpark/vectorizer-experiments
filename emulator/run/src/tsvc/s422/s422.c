/* TSVC_EMULATE_GENERATED: s422 */
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
    //    storage classes and equivalencing
    //    common and equivalence statement
    //    anti-dependence, threshold of 4


        xx = flat_2d_array + 4;

    for (int i = 0; i < LEN_1D; i++) {
        xx[i] = flat_2d_array[i + 8] + a[i];
    }
}
