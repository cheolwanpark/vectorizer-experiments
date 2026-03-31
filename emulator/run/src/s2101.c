/**
 * s2101 - Diagonals: Main Diagonal Calculation
 *
 * Tests strided (diagonal) access on 2D arrays.
 * Access pattern: aa[i][i] with stride = LEN_2D+1.
 *
 * TSVC Category: Diagonals
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_2D; i++) {
        aa[i][i] += bb[i][i] * cc[i][i];
    }
}
