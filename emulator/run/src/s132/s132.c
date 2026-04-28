/* TSVC_EMULATE_GENERATED: s132 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    global data flow analysis
    //    loop with multiple dimension ambiguous subscripts


        int m = 0;
        int j = m;
        int k = m+1;
    for (int i= 1; i < LEN_2D; i++) {
        aa[j][i] = aa[k][i-1] + b[i] * c[1];
    }
}
