/* TSVC_EMULATE_GENERATED: s122 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    induction variable recognition
    //    variable lower and upper bound, and stride
    //    reverse data access and jump in data access

        int n1 = tsvc_n1;
        int n3 = tsvc_n3;


        int j, k;
    j = 1;
    k = 0;
    for (int i = n1-1; i < LEN_1D; i += n3) {
        k += j;
        a[i] += b[LEN_1D - k];
    }
}
