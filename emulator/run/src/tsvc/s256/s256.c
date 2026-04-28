/* TSVC_EMULATE_GENERATED: s256 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    array expansion


    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 1; j < LEN_2D; j++) {
            a[j] = (real_t)1.0 - a[j - 1];
            aa[j][i] = a[j] + bb[j][i]*d[j];
        }
    }
}
