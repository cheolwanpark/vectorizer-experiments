/* TSVC_EMULATE_GENERATED: s1112 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    loop reversal


    for (int i = LEN_1D - 1; i >= 0; i--) {
        a[i] = b[i] + (real_t) 1.;
    }
}
