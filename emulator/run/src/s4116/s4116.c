/* TSVC_EMULATE_GENERATED: s4116 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    indirect addressing
    //    more complicated sparse sdot
    //    gather is required

        int * __restrict__ ip = tsvc_ip;
        int j = LEN_2D/2;
        int inc = tsvc_n1;


        real_t sum;
        int off;
    sum = 0.;
    for (int i = 0; i < LEN_2D-1; i++) {
        off = inc + i;
        sum += a[off] * aa[j-1][ip[i]];
    }
}
