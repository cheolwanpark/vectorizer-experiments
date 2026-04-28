/**
 * TSVC s251 - Scalar expansion
 * Tests scalar expansion where temporary holds intermediate result
 * Pattern: s = b[i] + c[i] * d[i]; a[i] = s * s
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        real_t s = b[i] + c[i] * d[i];
        a[i] = s * s;
    }
}
