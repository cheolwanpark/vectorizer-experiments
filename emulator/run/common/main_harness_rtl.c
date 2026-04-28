#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern volatile uint64_t tohost;
extern int WORKLOAD_ENTRY(int argc, char **argv);

__attribute__((weak))
int workload_verify(void) {
    return 1;
}

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
    int rc;
    int ok;
    uint64_t start = rdcycle();
    rc = WORKLOAD_ENTRY(0, 0);
    uint64_t end = rdcycle();

    dummy();
    measured_cycles = end - start;
    ok = (rc == 0) && workload_verify();
    tohost = ok ? 1 : 3;
    while (1) {
    }
    return 0;
}
