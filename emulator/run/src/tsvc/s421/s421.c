/**
 * s421 - Storage Classes: Equivalence, Forward Read
 *
 * Tests forward dependency: c[i] = c[i+1] + a[i].
 * Original uses xx/yy aliases; simplified to direct array.
 * LEN=4097 recommended (trip count = LEN_1D - 1).
 *
 * TSVC Category: Storage Classes
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D - 1; i++) {
        c[i] = c[i + 1] + a[i];
    }
}
