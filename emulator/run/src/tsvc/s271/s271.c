/**
 * s271 - Control Flow: If-conversion (Singularity Handling)
 *
 * TSVC Original Pattern:
 *   for (int i = 0; i < LEN; i++) {
 *       if (b[i] > (TYPE)0.)
 *           a[i] += b[i] * c[i];
 *   }
 *
 * Tests conditional/masked vector operations.
 * Compiler must convert control flow into predicated execution.
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.)
            a[i] += b[i] * c[i];
    }
}
