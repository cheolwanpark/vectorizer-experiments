/* TSVC_EMULATE_GENERATED: s292 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop peeling
    //    wrap around variable, 2 levels
    //    similar to S291


        int im1, im2;
    im1 = LEN_1D-1;
    im2 = LEN_1D-2;
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = (b[i] + b[im1] + b[im2]) * (real_t).333;
        im2 = im1;
        im1 = i;
    }
}
