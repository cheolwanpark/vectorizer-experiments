/* TSVC_EMULATE_GENERATED: s272 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    loop with independent conditional

        int t = tsvc_s1;


    for (int i = 0; i < LEN_1D; i++) {
        if (e[i] >= t) {
            a[i] += c[i] * d[i];
            b[i] += c[i] * c[i];
        }
    }
}
