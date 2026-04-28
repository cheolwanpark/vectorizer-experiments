/* TSVC_EMULATE_GENERATED: s319 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    reductions
    //    coupled reductions


        real_t sum;
    sum = 0.;
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = c[i] + d[i];
        sum += a[i];
        b[i] = c[i] + e[i];
        sum += b[i];
    }
}
