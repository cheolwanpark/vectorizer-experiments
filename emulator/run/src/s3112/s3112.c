/* TSVC_EMULATE_GENERATED: s3112 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    sum reduction saving running sums


        real_t sum;
    sum = (real_t)0.0;
    for (int i = 0; i < LEN_1D; i++) {
        sum += a[i];
        b[i] = sum;
    }
}
