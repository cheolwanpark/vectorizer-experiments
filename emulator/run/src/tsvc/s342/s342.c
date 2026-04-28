/* TSVC_EMULATE_GENERATED: s342 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    packing
    //    unpacking
    //    not vectorizable, value of j in unknown at each iteration


        int j = 0;
    j = -1;
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > (real_t)0.) {
            j++;
            a[i] = b[j];
        }
    }
}
