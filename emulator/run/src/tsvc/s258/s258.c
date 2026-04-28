/* TSVC_EMULATE_GENERATED: s258 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    wrap-around scalar under an if


        real_t s;
    s = 0.;
    for (int i = 0; i < LEN_2D; ++i) {
        if (a[i] > 0.) {
            s = d[i] * d[i];
        }
        b[i] = s * c[i] + d[i];
        e[i] = (s + (real_t)1.) * aa[0][i];
    }
}
