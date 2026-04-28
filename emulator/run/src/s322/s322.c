/* TSVC_EMULATE_GENERATED: s322 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    recurrences
    //    second order linear recurrence


    for (int i = 2; i < LEN_1D; i++) {
        a[i] = a[i] + a[i - 1] * b[i] + a[i - 2] * c[i];
    }
}
