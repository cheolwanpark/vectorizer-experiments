/**
 * s452 - Intrinsic Functions: Sequence Function
 *
 * Tests induction variable used in FP computation.
 * a[i] = b[i] + c[i] * (i+1) requires vid.v or similar.
 *
 * TSVC Category: Intrinsic Functions
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = b[i] + c[i] * (real_t)(i + 1);
    }
}
