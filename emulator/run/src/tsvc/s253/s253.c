/**
 * s253 - Scalar Expansion: Assigned Under If
 *
 * Tests conditional scalar expansion with predicated stores.
 * Scalar s only assigned/used under if condition.
 *
 * TSVC Category: Scalar Expansion
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > b[i]) {
            real_t s = a[i] - b[i] * d[i];
            c[i] += s;
            a[i] = s;
        }
    }
}
