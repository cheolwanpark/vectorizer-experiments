/**
 * s4117 - Indirect Addressing: Index Transformation
 *
 * Tests non-unit stride access via i/2 index transformation.
 * c[i/2] creates a gather-like access pattern.
 *
 * TSVC Category: Indirect Addressing
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = b[i] + c[i / 2] * d[i];
    }
}
