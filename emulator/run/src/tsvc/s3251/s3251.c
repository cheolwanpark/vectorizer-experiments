/* TSVC_EMULATE_GENERATED: s3251 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    scalar expansion


    for (int i = 0; i < LEN_1D-1; i++){
        a[i+1] = b[i]+c[i];
        b[i]   = c[i]*e[i];
        d[i]   = a[i]*e[i];
    }
}
