/* TSVC_EMULATE_GENERATED: s233 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop interchange
    //    interchanging with one of two inner loops


    for (int i = 1; i < LEN_2D; i++) {
        for (int j = 1; j < LEN_2D; j++) {
            aa[j][i] = aa[j-1][i] + cc[j][i];
        }
        for (int j = 1; j < LEN_2D; j++) {
            bb[j][i] = bb[j][i-1] + cc[j][i];
        }
    }
}
