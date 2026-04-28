/* TSVC_EMULATE_GENERATED: s242 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    node splitting

        real_t s1 = tsvc_s1;
        real_t s2 = tsvc_s2;


    for (int i = 1; i < LEN_1D; ++i) {
        a[i] = a[i - 1] + s1 + s2 + b[i] + c[i] + d[i];
    }
}
