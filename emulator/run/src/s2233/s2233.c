/**
 * s2233 - Loop Interchange: Two Inner Loops
 *
 * Tests 2D loop interchange with FOR dependency pattern.
 * Inner loops: j=1..LEN_2D with j-1 dependency.
 *
 * TSVC Category: Loop Interchange
 */
#include "common.h"

void kernel(void) {
    for (int i = 1; i < LEN_2D; i++) {
        for (int j = 1; j < LEN_2D; j++) {
            aa[j][i] = aa[j - 1][i] + cc[j][i];
        }
        for (int j = 1; j < LEN_2D; j++) {
            bb[i][j] = bb[i - 1][j] + cc[i][j];
        }
    }
}
