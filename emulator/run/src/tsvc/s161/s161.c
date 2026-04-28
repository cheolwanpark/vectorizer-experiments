/* TSVC_EMULATE_GENERATED: s161 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    tests for recognition of loop independent dependences
    //    between statements in mutually exclusive regions.


            for (int i = 0; i < LEN_1D-1; ++i) {
                if (b[i] < (real_t)0.) {
                    goto L20;
                }
                a[i] = c[i] + d[i] * e[i];
                goto L10;
    L20:
                c[i+1] = a[i] + d[i] * d[i];
    L10:
                ;
            }
}
