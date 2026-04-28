#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern volatile uint64_t tohost;
extern volatile uint64_t fromhost;
extern int WORKLOAD_ENTRY(int argc, char **argv);

static inline uint64_t rdcycle(void) {
    uint64_t c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

static void print_char(char ch) {
    volatile uint64_t magic_mem[8] __attribute__((aligned(64)));

    magic_mem[0] = 64;
    magic_mem[1] = 1;
    magic_mem[2] = (uint64_t)&ch;
    magic_mem[3] = 1;
    __sync_synchronize();
    tohost = (uint64_t)magic_mem;
    while (fromhost == 0) {
    }
    fromhost = 0;
}

static void print_str(const char *s) {
    while (*s) {
        print_char(*s++);
    }
}

static void print_dec(uint64_t n) {
    char buf[24];
    int i = 22;

    buf[23] = '\0';
    if (n == 0) {
        buf[i--] = '0';
    } else {
        while (n > 0) {
            buf[i--] = '0' + (n % 10);
            n /= 10;
        }
    }
    print_str(&buf[i + 1]);
}

__attribute__((noinline))
static void dummy(void) {
    __asm__ volatile("" ::: "memory");
}

int main(void) {
    uint64_t start = rdcycle();
    (void)WORKLOAD_ENTRY(0, 0);
    uint64_t end = rdcycle();

    dummy();
    print_str("cycles=");
    print_dec(end - start);
    print_str("\n");

    tohost = 1;
    while (1) {
    }
    return 0;
}
