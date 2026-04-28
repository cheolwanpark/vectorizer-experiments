/* TSVC_EMULATE_GENERATED: s114 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    linear dependence testing
    //    transpose vectorization
    //    Jump in data access - not vectorizable


    for (int i = 0; i < LEN_2D; i++) {
        for (int j = 0; j < i; j++) {
            aa[i][j] = aa[j][i] + bb[i][j];
        }
    }
}
