/* TSVC_EMULATE_GENERATED: s243 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    node splitting
    //    false dependence cycle breaking


    for (int i = 0; i < LEN_1D-1; i++) {
        a[i] = b[i] + c[i  ] * d[i];
        b[i] = a[i] + d[i  ] * e[i];
        a[i] = b[i] + a[i+1] * d[i];
    }
}
