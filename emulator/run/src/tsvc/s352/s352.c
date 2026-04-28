/* TSVC_EMULATE_GENERATED: s352 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop rerolling
    //    unrolled dot product


        real_t dot;
    dot = (real_t)0.;
    for (int i = 0; i < LEN_1D; i += 5) {
        dot = dot + a[i] * b[i] + a[i + 1] * b[i + 1] + a[i + 2]
            * b[i + 2] + a[i + 3] * b[i + 3] + a[i + 4] * b[i + 4];
    }
}
