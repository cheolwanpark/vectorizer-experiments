/* TSVC_EMULATE_GENERATED: s221 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop distribution
    //    loop that is partially recursive


    for (int i = 1; i < LEN_1D; i++) {
        a[i] += c[i] * d[i];
        b[i] = b[i - 1] + a[i] + d[i];
    }
}
