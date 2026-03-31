#include "common.h"

void kernel(void) {
    for (int i = 0; i < LEN_1D; i++) {
        if (b[i] > (real_t)0.) {
            a[i] += b[i] * c[i];
        }
    }
}
