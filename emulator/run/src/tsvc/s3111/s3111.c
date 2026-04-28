/* TSVC_EMULATE_GENERATED: s3111 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    conditional sum reduction


        real_t sum;
    sum = 0.;
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > (real_t)0.) {
            sum += a[i];
        }
    }
}
