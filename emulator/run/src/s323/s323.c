/* TSVC_EMULATE_GENERATED: s323 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    recurrences
    //    coupled recurrence


    for (int i = 1; i < LEN_1D; i++) {
        a[i] = b[i-1] + c[i] * d[i];
        b[i] = a[i] + c[i] * e[i];
    }
}
