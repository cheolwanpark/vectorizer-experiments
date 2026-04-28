/**
 * s252 - Scalar Expansion: Ambiguous Scalar Temporary
 *
 * Tests loop-carried scalar dependency: a[i] = s + t; t = s.
 * First-order recurrence through scalar variable t.
 *
 * TSVC Category: Scalar Expansion
 */
#include "common.h"

void kernel(void) {
    real_t t = (real_t)0.;
    real_t s;
    for (int i = 0; i < LEN_1D; i++) {
        s = b[i] * c[i];
        a[i] = s + t;
        t = s;
    }
}
