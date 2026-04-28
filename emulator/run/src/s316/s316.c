/* TSVC_EMULATE_GENERATED: s316 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    if to min reduction


        real_t x;
    x = a[0];
    for (int i = 1; i < LEN_1D; ++i) {
        if (a[i] < x) {
            x = a[i];
        }
    }
}
