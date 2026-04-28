/* TSVC_EMULATE_GENERATED: s1244 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    node splitting
    //    cycle with ture and anti dependency


    for (int i = 0; i < LEN_1D-1; i++) {
        a[i] = b[i] + c[i] * c[i] + b[i]*b[i] + c[i];
        d[i] = a[i] + a[i+1];
    }
}
