/**
 * vif - Vector If (Conditional Assignment)
 *
 * Tests simple masked vector store: conditional a[i] = b[i].
 * Clean if-conversion to masked operation.
 *
 * TSVC Category: Control Loops
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.) {
            a[i] = b[i];
        }
    }
}
