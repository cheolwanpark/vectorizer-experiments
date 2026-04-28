/* TSVC_EMULATE_GENERATED: s1111 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    no dependence - vectorizable
    //    jump in data access


    for (int i = 0; i < LEN_1D/2; i++) {
        a[2*i] = c[i] * b[i] + d[i] * b[i] + c[i] * c[i] + d[i] * b[i] + d[i] * c[i];
    }
}
