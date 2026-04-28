/**
 * s313 - Reductions: Dot Product
 *
 * Tests dot product reduction: dot += a[i] * b[i].
 * Requires -ffast-math for vfredusum.vs (unordered reduction).
 *
 * TSVC Category: Reductions
 */
#include "common.h"

void kernel(void) {
    real_t dot = (real_t)0.;
    for (int i = 0; i < LEN_1D; i++) {
        dot += a[i] * b[i];
    }
    volatile real_t result = dot;
    (void)result;
}
