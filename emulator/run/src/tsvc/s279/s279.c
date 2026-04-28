/**
 * s279 - Control Flow: Complex Vector If/Gotos
 *
 * Tests multiple goto-based branches within a single loop.
 * More complex if-conversion challenge than s278.
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > (real_t)0.) {
            goto L20;
        }
        b[i] = -b[i] + d[i] * d[i];
        if (b[i] <= a[i]) {
            goto L30;
        }
        c[i] += d[i] * e[i];
        goto L30;
L20:
        c[i] = -c[i] + e[i] * e[i];
L30:
        a[i] = b[i] + c[i] * d[i];
    }
}
