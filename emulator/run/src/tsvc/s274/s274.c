/* TSVC_EMULATE_GENERATED: s274 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    complex loop with dependent conditional


    for (int i = 0; i < LEN_1D; i++) {
        a[i] = c[i] + e[i] * d[i];
        if (a[i] > (real_t)0.) {
            b[i] = a[i] + b[i];
        } else {
            a[i] = d[i] * e[i];
        }
    }
}
