/**
 * RTL Simulation Harness
 *
 * For Chipyard/Verilator simulations where HTIF syscalls don't work.
 * No print output - cycles are extracted from verbose trace (mcycle CSR reads).
 */
#include "types.h"
#include "arrays.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY kernel
#endif

extern void WORKLOAD_ENTRY(void);

extern volatile uint64_t tohost;

static inline uint64_t rdcycle(void) {
    uint64_t c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

__attribute__((noinline))
static void dummy(void) {
    __asm__ volatile("" ::: "memory");
}

/* Store cycles in a known location for easy extraction */
volatile uint64_t measured_cycles __attribute__((section(".data")));

int main(void) {
    /* Warmup run */
    init_arrays();
    WORKLOAD_ENTRY();
    dummy();

    /* Timed run */
    init_arrays();
    uint64_t start = rdcycle();
    WORKLOAD_ENTRY();
    uint64_t end = rdcycle();
    dummy();

    measured_cycles = end - start;

    /* Signal completion - tohost=1 means success */
    tohost = 1;
    while (1);
    return 0;
}
