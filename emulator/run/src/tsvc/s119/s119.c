/* TSVC_EMULATE_GENERATED: s119 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    no dependence - vectorizable


    for (int i = 1; i < LEN_2D; i++) {
        for (int j = 1; j < LEN_2D; j++) {
            aa[i][j] = aa[i-1][j-1] + bb[i][j];
        }
    }
}
