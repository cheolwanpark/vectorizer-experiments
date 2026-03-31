/**
 * s131 - Global Data Flow: Forward Substitution
 *
 * Tests forward read dependency: a[i] = a[i+1] + b[i].
 * LEN=4097 recommended (trip count = LEN_1D - 1).
 *
 * TSVC Category: Global Data Flow Analysis
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D - 1; i++) {
        a[i] = a[i + 1] + b[i];
    }
}
