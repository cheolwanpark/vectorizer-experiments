/**
 * vag - Vector Assignment, Gather
 *
 * Tests indexed/gather load: a[i] = b[indx[i]].
 * Generates vluxei (indexed vector load).
 *
 * TSVC Category: Control Loops
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        a[i] = b[indx[i]];
    }
}
