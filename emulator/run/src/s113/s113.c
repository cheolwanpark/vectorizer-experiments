/* TSVC_EMULATE_GENERATED: s113 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    a(i)=a(1) but no actual dependence cycle


    for (int i = 1; i < LEN_1D; i++) {
        a[i] = a[0] + b[i];
    }
}
