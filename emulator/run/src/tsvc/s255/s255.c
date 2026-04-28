/* TSVC_EMULATE_GENERATED: s255 */
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
    //    scalar and array expansion
    //    carry around variables, 2 levels


        real_t x, y;
    x = b[LEN_1D-1];
    y = b[LEN_1D-2];
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = (b[i] + x + y) * (real_t).333;
        y = x;
        x = b[i];
    }
}
