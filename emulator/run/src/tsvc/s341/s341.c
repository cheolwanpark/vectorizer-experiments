/* TSVC_EMULATE_GENERATED: s341 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    packing
    //    pack positive values
    //    not vectorizable, value of j in unknown at each iteration


        int j;
    j = -1;
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.) {
            j++;
            a[j] = b[i];
        }
    }
}
