/* TSVC_EMULATE_GENERATED: s431 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    parameters
    //    parameter statement

        int k1=1;
        int k2=2;
        int k=2*k1-k2;


    for (int i = 0; i < LEN_1D; i++) {
        a[i] = a[i+k] + b[i];
    }
}
