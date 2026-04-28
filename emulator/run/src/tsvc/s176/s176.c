/* TSVC_EMULATE_GENERATED: s176 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    symbolics
    //    convolution


        int m = LEN_1D/2;
    for (int j = 0; j < (LEN_1D/2); j++) {
        for (int i = 0; i < m; i++) {
            a[i] += b[i+m-j-1] * c[j];
        }
    }
}
