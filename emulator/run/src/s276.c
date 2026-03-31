/**
 * s276 - Control Flow: If Test Using Loop Index
 *
 * Tests branch on loop induction variable (not data-dependent).
 * Compiler can split loop at midpoint instead of using masks.
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    int mid = (LEN_1D / 2);
    for (int i = 0; i < LEN_1D; i++) {
        if (i + 1 < mid) {
            a[i] += b[i] * c[i];
        } else {
            a[i] += b[i] * d[i];
        }
    }
}
