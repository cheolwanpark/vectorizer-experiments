/* TSVC_EMULATE_GENERATED: s4113 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    indirect addressing
    //    indirect addressing on rhs and lhs
    //    gather and scatter is required

        int * __restrict__ ip = tsvc_ip;


    for (int i = 0; i < LEN_1D; i++) {
        a[ip[i]] = b[ip[i]] + c[i];
    }
}
