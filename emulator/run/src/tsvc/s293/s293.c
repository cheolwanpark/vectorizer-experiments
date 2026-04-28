/* TSVC_EMULATE_GENERATED: s293 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop peeling
    //    a(i)=a(0) with actual dependence cycle, loop is vectorizable


    for (int i = 0; i < LEN_1D; i++) {
        a[i] = a[0];
    }
}
