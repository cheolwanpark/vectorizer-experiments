/* TSVC_EMULATE_GENERATED: s291 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop peeling
    //    wrap around variable, 1 level


        int im1;
    im1 = LEN_1D-1;
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = (b[i] + b[im1]) * (real_t).5;
        im1 = i;
    }
}
