#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern int WORKLOAD_ENTRY(int argc, char **argv);

__attribute__((weak))
int workload_verify(void) {
    return 1;
}

#define VICUNA_UART_DATA   (*(volatile unsigned int *)0xFF000000)
#define VICUNA_UART_STATUS (*(volatile unsigned int *)0xFF000004)

static inline unsigned int rdcycle(void) {
    unsigned int c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

static void uart_putc(char ch) {
    while (VICUNA_UART_STATUS & 1) {
    }
    VICUNA_UART_DATA = (unsigned int)ch;
}

static void print_str(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

static void print_dec(unsigned int n) {
    char buf[12];
    int i = 10;

    buf[11] = '\0';
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

volatile unsigned int measured_cycles __attribute__((section(".data")));

int main(void) {
    unsigned int start = rdcycle();
    int rc = WORKLOAD_ENTRY(0, 0);
    unsigned int end = rdcycle();
    int ok = (rc == 0) && workload_verify();

    dummy();
    measured_cycles = end - start;
    print_str("cycles=");
    print_dec(end - start);
    print_str("\n");
    print_str(ok ? "PASSED\n" : "FAILED\n");
    return ok ? 0 : 1;
}
