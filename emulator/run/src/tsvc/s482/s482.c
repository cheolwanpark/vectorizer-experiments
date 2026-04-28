/* TSVC_EMULATE_GENERATED: s482 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    non-local goto's
    //    other loop exit with code before exit


    for (int i = 0; i < LEN_1D; i++) {
        a[i] += b[i] * c[i];
        if (c[i] > b[i]) break;
    }
}
