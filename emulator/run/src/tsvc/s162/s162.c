/* TSVC_EMULATE_GENERATED: s162 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    control flow
    //    deriving assertions

        int k = tsvc_n1;


    if (k > 0) {
        for (int i = 0; i < LEN_1D-1; i++) {
            a[i] = a[i + k] + b[i] * c[i];
        }
    }
}
