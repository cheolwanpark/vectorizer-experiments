/* TSVC_EMULATE_GENERATED: s261 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    wrap-around scalar under an if


        real_t t;
    for (int i = 1; i < LEN_1D; ++i) {
        t = a[i] + b[i];
        a[i] = t + c[i-1];
        t = c[i] * d[i];
        c[i] = t;
    }
}
