/* TSVC_EMULATE_GENERATED: s4114 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    indirect addressing
    //    mix indirect addressing with variable lower and upper bounds
    //    gather is required

        int * __restrict__ ip = tsvc_ip;
        int n1 = tsvc_n1;


        int k;
    for (int i = n1-1; i < LEN_1D; i++) {
        k = ip[i];
        a[i] = b[i] + c[LEN_1D-k+1-2] * d[i];
        k += 5;
    }
}
