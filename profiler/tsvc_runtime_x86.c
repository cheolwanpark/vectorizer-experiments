/**
 * Minimal TSVC runtime for x86 native profiling.
 *
 * Provides extern symbols referenced by generated benchmark sources
 * (converted from TSVC_2 loops by benchmark_sources.py).
 * Unlike emulator/run/common/tsvc_runtime.c, this links against the
 * standard C library and does not provide baremetal shims.
 */
#include <stddef.h>
#include <stdlib.h>
#include <math.h>
#include "types.h"

int *tsvc_ip;
int tsvc_n1 = 1;
int tsvc_n3 = 1;
real_t tsvc_s1;
real_t tsvc_s2;

__attribute__((weak)) real_t test(real_t *A) {
    real_t sum = (real_t)0.0f;
    if (A == NULL) return sum;
    for (int i = 0; i < 4; i++) sum += A[i];
    return sum;
}

__attribute__((weak)) real_t f(real_t a, real_t b) {
    return a * b;
}
