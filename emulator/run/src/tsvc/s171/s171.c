/* TSVC_EMULATE_GENERATED: s171 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    symbolics
    //    symbolic dependence tests

        int inc = tsvc_n1;


    for (int i = 0; i < LEN_1D; i++) {
        a[i * inc] += b[i];
    }
}
