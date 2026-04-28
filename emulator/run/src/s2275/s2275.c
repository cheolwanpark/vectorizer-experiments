/* TSVC_EMULATE_GENERATED: s2275 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop distribution is needed to be able to interchange


    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            aa[j][i] = aa[j][i] + bb[j][i] * cc[j][i];
        }
        a[i] = b[i] + c[i] * d[i];
    }
}
