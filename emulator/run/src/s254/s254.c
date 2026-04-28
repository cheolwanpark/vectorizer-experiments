/**
 * s254 - Scalar Expansion: Carry Around Variable
 *
 * Tests loop-carried dependency via scalar carry-around.
 * x carries b[i] from previous iteration.
 *
 * TSVC Category: Scalar Expansion
 */
#include "common.h"

void kernel(void) {
    real_t x = b[LEN_1D - 1];
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = (b[i] + x) * (real_t).5;
        x = b[i];
    }
}
