/* TSVC_EMULATE_GENERATED: s2251 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    scalar expansion


    real_t s = (real_t)0.0;
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = s*e[i];
        s = b[i]+c[i];
        b[i] = a[i]+d[i];
    }
}
