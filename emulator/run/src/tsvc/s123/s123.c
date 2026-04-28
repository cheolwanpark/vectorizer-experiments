/* TSVC_EMULATE_GENERATED: s123 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    induction variable recognition
    //    induction variable under an if
    //    not vectorizable, the condition cannot be speculated


        int j;
    j = -1;
    for (int i = 0; i < (LEN_1D/2); i++) {
        j++;
        a[j] = b[i] + d[i] * e[i];
        if (c[i] > (real_t)0.) {
            j++;
            a[j] = c[i] + d[i] * e[i];
        }
    }
}
