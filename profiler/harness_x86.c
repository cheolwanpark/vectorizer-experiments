/**
 * x86 Native Profiling Harness
 *
 * Uses LFENCE+RDTSC / RDTSCP+LFENCE for serialized cycle measurement.
 * Outputs "KC=<best_cycles>" matching the RISC-V harness convention.
 *
 * Note: RDTSC reads the invariant TSC which ticks at a fixed reference
 * frequency on modern Intel (Skylake+). This is suitable for relative
 * comparisons between VF choices on the same machine.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "arrays.h"

extern void kernel(void);

static inline uint64_t rdtsc_start(void) {
    unsigned int lo, hi;
    __asm__ volatile("lfence\n\trdtsc" : "=a"(lo), "=d"(hi) :: "memory");
    return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t rdtsc_end(void) {
    unsigned int lo, hi;
    __asm__ volatile("rdtscp" : "=a"(lo), "=d"(hi) :: "ecx");
    __asm__ volatile("lfence" ::: "memory");
    return ((uint64_t)hi << 32) | lo;
}

int main(int argc, char **argv) {
    int warmup = 3;
    int repeat = 10;

    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "--warmup=", 9) == 0)
            warmup = atoi(argv[i] + 9);
        else if (strncmp(argv[i], "--repeat=", 9) == 0)
            repeat = atoi(argv[i] + 9);
    }

    for (int w = 0; w < warmup; w++) {
        init_arrays();
        kernel();
    }

    uint64_t best = UINT64_MAX;
    for (int r = 0; r < repeat; r++) {
        init_arrays();
        uint64_t start = rdtsc_start();
        kernel();
        uint64_t end = rdtsc_end();
        uint64_t elapsed = end - start;
        if (elapsed < best)
            best = elapsed;
        printf("run=%d cycles=%lu\n", r, (unsigned long)elapsed);
    }
    printf("KC=%lu\n", (unsigned long)best);
    return 0;
}
