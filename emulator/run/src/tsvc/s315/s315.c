/* TSVC_EMULATE_GENERATED: s315 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    if to max with index reductio 1 dimension


        for (int i = 0; i < LEN_1D; i++)
            a[i] = (i * 7) % LEN_1D;

        real_t x, chksum;
        int index;
    x = a[0];
    index = 0;
    for (int i = 0; i < LEN_1D; ++i) {
        if (a[i] > x) {
            x = a[i];
            index = i;
        }
    }
    chksum = x + (real_t) index;
}
