/* TSVC_EMULATE_GENERATED: s281 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    crossing thresholds
    //    index set splitting
    //    reverse data access


        real_t x;
    for (int i = 0; i < LEN_1D; i++) {
        x = a[LEN_1D-i-1] + b[i] * c[i];
        a[i] = x-(real_t)1.0;
        b[i] = x;
    }
}
