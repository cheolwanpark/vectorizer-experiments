/* TSVC_EMULATE_GENERATED: s273 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    simple loop with dependent conditional


    for (int i = 0; i < LEN_1D; i++) {
        a[i] += d[i] * e[i];
        if (a[i] < (real_t)0.)
            b[i] += d[i] * e[i];
        c[i] += a[i] * d[i];
    }
}
