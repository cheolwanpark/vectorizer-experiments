/**
 * s332 - Search Loops: First Value Greater Than Threshold
 *
 * Tests early-exit search loop with goto.
 * Vectorization extremely challenging due to break semantics.
 *
 * TSVC Category: Search Loops
 */
#include "common.h"

void kernel(void) {
    int index = -2;
    real_t value = (real_t)-1.;
    real_t threshold = (real_t)0.5;
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > threshold) {
            index = i;
            value = a[i];
            goto L20;
        }
    }
L20:
    ;
    volatile int res_index = index;
    volatile real_t res_value = value;
    (void)res_index;
    (void)res_value;
}
