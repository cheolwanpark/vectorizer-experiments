/* TSVC_EMULATE_GENERATED: s235 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop interchanging
    //    imperfectly nested loops


    for (int i = 0; i < LEN_2D; i++) {
        a[i] += b[i] * c[i];
        for (int j = 1; j < LEN_2D; j++) {
            aa[j][i] = aa[j-1][i] + bb[j][i] * a[i];
        }
    }
}
