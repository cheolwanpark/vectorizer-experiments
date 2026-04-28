/* TSVC_EMULATE_GENERATED: s2711 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    semantic if removal


    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] != (real_t)0.0) {
            a[i] += b[i] * c[i];
        }
    }
}
