/* TSVC_EMULATE_GENERATED: s31111 */
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
    //    reductions
    //    sum reduction


        real_t sum;
    sum = (real_t)0.;
    sum += test(a);
    sum += test(&a[4]);
    sum += test(&a[8]);
    sum += test(&a[12]);
    sum += test(&a[16]);
    sum += test(&a[20]);
    sum += test(&a[24]);
    sum += test(&a[28]);
}
