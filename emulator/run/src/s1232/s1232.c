/* TSVC_EMULATE_GENERATED: s1232 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    loop interchange
    //    interchanging of triangular loops


    for (int j = 0; j < LEN_2D; j++) {
        for (int i = j; i < LEN_2D; i++) {
            aa[i][j] = bb[i][j] + cc[i][j];
        }
    }
}
