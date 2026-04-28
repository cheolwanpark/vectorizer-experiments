/* TSVC_EMULATE_GENERATED: s343 */
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
    //    packing
    //    pack 2-d array into one dimension
    //    not vectorizable, value of k in unknown at each iteration


        int k;
    k = -1;
    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            if (bb[j][i] > (real_t)0.) {
                k++;
                flat_2d_array[k] = aa[j][i];
            }
        }
    }
}
