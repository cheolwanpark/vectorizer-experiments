/* TSVC_EMULATE_GENERATED: s257 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    scalar and array expansion
    //    array expansion


    for (int i = 1; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            a[i] = aa[j][i] - a[i-1];
            aa[j][i] = a[i] + bb[j][i];
        }
    }
}
