/* TSVC_EMULATE_GENERATED: s173 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    symbolics
    //    expression in loop bounds and subscripts


        int k = LEN_1D/2;
    for (int i = 0; i < LEN_1D/2; i++) {
        a[i+k] = a[i] + b[i];
    }
}
