/* TSVC_EMULATE_GENERATED: s118 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    potential dot product recursion


    for (int i = 1; i < LEN_2D; i++) {
        for (int j = 0; j <= i - 1; j++) {
            a[i] += bb[j][i] * a[i-j-1];
        }
    }
}
