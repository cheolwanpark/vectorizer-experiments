/* TSVC_EMULATE_GENERATED: s172 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    symbolics
    //    vectorizable if n3 .ne. 0

        int n1 = tsvc_n1;
        int n3 = tsvc_n3;


    for (int i = n1-1; i < LEN_1D; i += n3) {
        a[i] += b[i];
    }
}
