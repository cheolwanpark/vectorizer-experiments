/**
 * vas - Vector Assignment, Scatter
 *
 * Tests indexed/scatter store: a[indx[i]] = b[i].
 * Generates vsuxei (indexed vector store).
 *
 * TSVC Category: Control Loops
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[indx[i]] = b[i];
    }
}
