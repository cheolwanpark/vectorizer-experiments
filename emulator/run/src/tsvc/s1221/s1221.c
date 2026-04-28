/* TSVC_EMULATE_GENERATED: s1221 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    run-time symbolic resolution


    for (int i = 4; i < LEN_1D; i++) {
        b[i] = b[i - 4] + a[i];
    }
}
