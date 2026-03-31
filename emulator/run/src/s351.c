/**
 * s351 - Loop Rerolling: Unrolled SAXPY
 *
 * Tests compiler loop rerolling of manually unrolled SAXPY.
 * Step-5 loop body handles 5 elements per iteration.
 *
 * TSVC Category: Loop Rerolling
 */
#include "common.h"

void kernel(void) {
    real_t alpha = c[0];
    for (int i = 0; i < LEN_1D; i += 5) {
        a[i] += alpha * b[i];
        a[i + 1] += alpha * b[i + 1];
        a[i + 2] += alpha * b[i + 2];
        a[i + 3] += alpha * b[i + 3];
        a[i + 4] += alpha * b[i + 4];
    }
}
