/**
 * s443 - Non-Logical Ifs: Arithmetic If
 *
 * Tests goto-based arithmetic if (two-way branch).
 * Simple if-conversion candidate.
 *
 * TSVC Category: Non-Logical Ifs
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (d[i] <= (real_t)0.) {
            goto L20;
        } else {
            goto L30;
        }
L20:
        a[i] += b[i] * c[i];
        goto L50;
L30:
        a[i] += b[i] * b[i];
L50:
        ;
    }
}
