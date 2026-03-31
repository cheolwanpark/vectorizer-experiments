/**
 * s1279 - Control Flow: Nested Vector If/Gotos
 *
 * Tests nested conditional with two vector comparisons.
 * Both conditions are data-dependent (a[i], b[i]).
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] < (real_t)0.) {
            if (b[i] > a[i]) {
                c[i] += d[i] * e[i];
            }
        }
    }
}
