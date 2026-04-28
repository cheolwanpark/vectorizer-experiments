/* TSVC_EMULATE_GENERATED: s1115 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    triangular saxpy loop


    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            aa[i][j] = aa[i][j]*cc[j][i] + bb[i][j];
        }
    }
}
