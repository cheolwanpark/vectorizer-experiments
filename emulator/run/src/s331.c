/**
 * s331 - Search Loops: If to Last
 *
 * Tests search for last index where condition is true.
 * Vectorization challenge: conditional index update.
 *
 * TSVC Category: Search Loops
 */
#include "common.h"

void kernel(void) {
    int j = -1;
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] < (real_t)0.) {
            j = i;
        }
    }
    volatile int result = j;
    (void)result;
}
