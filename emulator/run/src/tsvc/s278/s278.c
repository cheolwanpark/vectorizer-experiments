/**
 * s278 - Control Flow: If/Goto to Block If-Then-Else
 *
 * Tests goto-based control flow conversion to predicated ops.
 * Equivalent to if-then-else with unconditional tail.
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > (real_t)0.) {
            goto L20;
        }
        b[i] = -b[i] + d[i] * e[i];
        goto L30;
L20:
        c[i] = -c[i] + d[i] * e[i];
L30:
        a[i] = b[i] + c[i] * d[i];
    }
}
