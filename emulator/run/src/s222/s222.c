/* TSVC_EMULATE_GENERATED: s222 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop distribution
    //    partial loop vectorizatio recurrence in middle


    for (int i = 1; i < LEN_1D; i++) {
        a[i] += b[i] * c[i];
        e[i] = e[i - 1] * e[i - 1];
        a[i] -= b[i] * c[i];
    }
}
