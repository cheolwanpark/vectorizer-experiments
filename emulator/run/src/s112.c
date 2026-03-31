/**
 * s112 - Linear Dependence Testing: Loop Reversal
 *
 * Tests reverse loop with forward write: a[i+1] = a[i] + b[i].
 * Reverse iteration enables vectorization of this dependency.
 * LEN=4097 recommended (trip count = LEN_1D - 1).
 *
 * TSVC Category: Linear Dependence Testing
 */
#include "common.h"

void kernel(void) {
    for (int i = LEN_1D - 2; i >= 0; i--) {
        a[i + 1] = a[i] + b[i];
    }
}
