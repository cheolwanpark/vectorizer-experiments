/* TSVC_EMULATE_GENERATED: s453 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    induction varibale recognition

        real_t s;


    s = 0.;
    for (int i = 0; i < LEN_1D; i++) {
        s += (real_t)2.;
        a[i] = s * b[i];
    }
}
