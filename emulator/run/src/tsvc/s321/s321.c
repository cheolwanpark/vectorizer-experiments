/* TSVC_EMULATE_GENERATED: s321 */
#include "common.h"

extern int *tsvc_ip;
extern int tsvc_n1;
extern int tsvc_n3;
extern real_t tsvc_s1;
extern real_t tsvc_s2;

void kernel(void) {
    //    recurrences
    //    first order linear recurrence


    for (int i = 1; i < LEN_1D; i++) {
        a[i] += a[i-1] * b[i];
    }
}
