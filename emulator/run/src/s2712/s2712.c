/* TSVC_EMULATE_GENERATED: s2712 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    if to elemental min


    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > b[i]) {
            a[i] += b[i] * c[i];
        }
    }
}
