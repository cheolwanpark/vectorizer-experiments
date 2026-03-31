/**
 * s1281 - Crossing Thresholds: Index Set Splitting
 *
 * Tests vectorization with multiple stores from same expression.
 * Pattern: x = expr; a[i] = x-1; b[i] = x;
 *
 * TSVC Category: Crossing Thresholds
 */
#include "common.h"

void kernel(void) {
    real_t x;
    for (int i = 0; i < LEN_1D; i++) {
        x = b[i] * c[i] + a[i] * d[i] + e[i];
        a[i] = x - (real_t)1.0;
        b[i] = x;
    }
}
