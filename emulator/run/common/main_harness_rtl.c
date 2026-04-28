#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern volatile uint64_t tohost;
extern int WORKLOAD_ENTRY(int argc, char **argv);

static inline uint64_t rdcycle(void) {
    uint64_t c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

__attribute__((noinline))
static void dummy(void) {
    __asm__ volatile("" ::: "memory");
}

volatile uint64_t measured_cycles __attribute__((section(".data")));

int main(void) {
    uint64_t start = rdcycle();
    (void)WORKLOAD_ENTRY(0, 0);
    uint64_t end = rdcycle();

    dummy();
    measured_cycles = end - start;
    tohost = 1;
    while (1) {
    }
    return 0;
}
