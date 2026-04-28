/**
 * s128 - Induction Variables: Coupled Induction Variables
 *
 * Tests coupled induction variables j, k with stride-2 access.
 * Trip count = LEN_1D/2.
 *
 * TSVC Category: Induction Variables
 */
#include "common.h"

void kernel(void) {
    int j = -1;
    int k;
    for (int i = 0; i < LEN_1D / 2; i++) {
        k = j + 1;
        a[i] = b[k] - d[i];
        j = k + 1;
        b[k] = a[i] + c[k];
    }
}
