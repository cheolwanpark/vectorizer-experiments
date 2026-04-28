/* TSVC_EMULATE_GENERATED: s471 */
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

int s471s(void)
{
// --  dummy subroutine call made in s471
    return 0;
}

void kernel(void) {
    //    call statements

        int m = LEN_1D;


    for (int i = 0; i < m; i++) {
        x[i] = b[i] + d[i] * d[i];
        s471s();
        b[i] = c[i] + d[i] * e[i];
    }
}
