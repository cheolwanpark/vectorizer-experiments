/**
 * TSVC s121 - Induction variable recognition
 * Tests induction variable recognition with forward dependency
 * Pattern: a[i] = a[i+1] + b[i]
 */
#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D - 1; i++) {
        a[i] = a[i + 1] + b[i];
    }
}
