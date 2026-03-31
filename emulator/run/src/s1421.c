/**
 * s1421 - Storage Classes: Equivalence, No Overlap
 *
 * Tests pointer aliasing with non-overlapping regions.
 * b[i] reads from upper half of b[], writes to lower half.
 *
 * TSVC Category: Storage Classes
 */
#include "common.h"

void kernel(void) {
    real_t *xx = &b[LEN_1D / 2];
    for (int i = 0; i < LEN_1D / 2; i++) {
        b[i] = xx[i] + a[i];
    }
}
