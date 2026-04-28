/* TSVC_EMULATE_GENERATED: s241 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    node splitting
    //    preloading necessary to allow vectorization


    for (int i = 0; i < LEN_1D-1; i++) {
        a[i] = b[i] * c[i  ] * d[i];
        b[i] = a[i] * a[i+1] * d[i];
    }
}
