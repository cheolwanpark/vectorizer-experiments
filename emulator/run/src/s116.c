/**
 * s116 - Linear Dependence Testing: Unrolled by 5
 *
 * Tests manually unrolled loop with intra-group dependencies.
 * a[i] = a[i+1]*a[i] pattern within each group of 5.
 *
 * TSVC Category: Linear Dependence Testing
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D - 5; i += 5) {
        a[i] = a[i + 1] * a[i];
        a[i + 1] = a[i + 2] * a[i + 1];
        a[i + 2] = a[i + 3] * a[i + 2];
        a[i + 3] = a[i + 4] * a[i + 3];
        a[i + 4] = a[i + 5] * a[i + 4];
    }
}
