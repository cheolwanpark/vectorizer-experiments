/* TSVC_EMULATE_GENERATED: s2102 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    diagonals
    //    identity matrix, best results vectorize both inner and outer loops


    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < LEN_2D; j++) {
            aa[j][i] = (real_t)0.;
        }
        aa[i][i] = (real_t)1.;
    }
}
