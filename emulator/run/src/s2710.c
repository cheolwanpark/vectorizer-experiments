/**
 * s2710 - Control Flow: Scalar and Vector Ifs (nested)
 *
 * Tests nested if-else with both scalar and vector conditions.
 * Compiler must handle mixed scalar/vector predication.
 *
 * TSVC Category: Control Flow
 */
#include "common.h"

void kernel(void) {
    int x = 1;
    for (int i = 0; i < LEN_1D; i++) {
        if (a[i] > b[i]) {
            a[i] += b[i] * d[i];
            if (LEN_1D > 10) {
                c[i] += d[i] * d[i];
            } else {
                c[i] = d[i] * e[i] + (real_t)1.;
            }
        } else {
            b[i] = a[i] + e[i] * e[i];
            if (x > (real_t)0.) {
                c[i] = a[i] + d[i] * d[i];
            } else {
                c[i] += e[i] * e[i];
            }
        }
    }
}
