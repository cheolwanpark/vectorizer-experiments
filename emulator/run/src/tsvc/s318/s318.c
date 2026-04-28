/* TSVC_EMULATE_GENERATED: s318 */
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
    //    isamax, max absolute value, increments not equal to 1

        int inc = tsvc_n1;


        int k, index;
        real_t max, chksum;
            k = 0;
            index = 0;
            max = ABS(a[0]);
            k += inc;
            for (int i = 1; i < LEN_1D; i++) {
                if (ABS(a[k]) <= max) {
                    goto L5;
                }
                index = i;
                max = ABS(a[k]);
    L5:
                k += inc;
            }
            chksum = max + (real_t) index;
}
