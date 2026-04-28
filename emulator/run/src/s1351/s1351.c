/* TSVC_EMULATE_GENERATED: s1351 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    induction pointer recognition


    real_t* __restrict__ A = a;
    real_t* __restrict__ B = b;
    real_t* __restrict__ C = c;
    for (int i = 0; i < LEN_1D; i++) {
        *A = *B+*C;
        A++;
        B++;
        C++;
    }
}
