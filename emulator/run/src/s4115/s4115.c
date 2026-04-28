/* TSVC_EMULATE_GENERATED: s4115 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    indirect addressing
    //    sparse dot product
    //    gather is required

        int * __restrict__ ip = tsvc_ip;


        real_t sum;
    sum = 0.;
    for (int i = 0; i < LEN_1D; i++) {
        sum += a[i] * b[ip[i]];
    }
}
