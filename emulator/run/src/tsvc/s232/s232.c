/* TSVC_EMULATE_GENERATED: s232 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop interchange
    //    interchanging of triangular loops


    for (int j = 1; j < LEN_2D; j++) {
        for (int i = 1; i <= j; i++) {
            aa[j][i] = aa[j][i-1]*aa[j][i-1]+bb[j][i];
        }
    }
}
