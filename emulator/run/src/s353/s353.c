/* TSVC_EMULATE_GENERATED: s353 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop rerolling
    //    unrolled sparse saxpy
    //    gather is required

        int * __restrict__ ip = tsvc_ip;


        real_t alpha = c[0];
    for (int i = 0; i < LEN_1D; i += 5) {
        a[i] += alpha * b[ip[i]];
        a[i + 1] += alpha * b[ip[i + 1]];
        a[i + 2] += alpha * b[ip[i + 2]];
        a[i + 3] += alpha * b[ip[i + 3]];
        a[i + 4] += alpha * b[ip[i + 4]];
    }
}
