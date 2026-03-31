/**
 * s124 - Induction Variable Recognition: Under Both If Branches
 *
 * Tests induction variable j incremented in both branches.
 * Since j always increments, compiler can recognize j == i.
 *
 * TSVC Category: Induction Variable Recognition
 */
#include "common.h"

void kernel(void) {
    int j = -1;
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.) {
            j++;
            a[j] = b[i] + d[i] * e[i];
        } else {
            j++;
            a[j] = c[i] + d[i] * e[i];
        }
    }
}
