/* TSVC_EMULATE_GENERATED: s277 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    test for dependences arising from guard variable computation.


            for (int i = 0; i < LEN_1D-1; i++) {
                    if (a[i] >= (real_t)0.) {
                        goto L20;
                    }
                    if (b[i] >= (real_t)0.) {
                        goto L30;
                    }
                    a[i] += c[i] * d[i];
    L30:
                    b[i+1] = c[i] + d[i] * e[i];
    L20:
    ;
            }
}
