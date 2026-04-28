/* TSVC_EMULATE_GENERATED: s423 */
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
    //    common and equivalenced variables - with anti-dependence

        // do this again here
        int vl = 64;
        xx = flat_2d_array + vl;


    for (int i = 0; i < LEN_1D - 1; i++) {
        flat_2d_array[i+1] = xx[i] + a[i];
    }
}
