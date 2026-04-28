/* TSVC_EMULATE_GENERATED: s441 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    non-logical if's
    //    arithmetic if


    for (int i = 0; i < LEN_1D; i++) {
        if (d[i] < (real_t)0.) {
            a[i] += b[i] * c[i];
        } else if (d[i] == (real_t)0.) {
            a[i] += b[i] * b[i];
        } else {
            a[i] += c[i] * c[i];
        }
    }
}
