/* TSVC_EMULATE_GENERATED: s491 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    vector semantics
    //    indirect addressing on lhs, store in sequence
    //    scatter is required

        int * __restrict__ ip = tsvc_ip;


    for (int i = 0; i < LEN_1D; i++) {
        a[ip[i]] = b[i] + c[i] * d[i];
    }
}
