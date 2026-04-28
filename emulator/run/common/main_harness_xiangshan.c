#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern int WORKLOAD_ENTRY(int argc, char **argv);

__attribute__((weak))
int workload_verify(void) {
    return 1;
}

#define UART_TX (*(volatile uint8_t *)0x40600004UL)

static void uart_putchar(char c) {
    UART_TX = (uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) {
        uart_putchar(*s++);
    }
}

static void uart_print_u64(uint64_t val) {
    char buf[20];
    int i = 0;

    if (val == 0) {
        uart_putchar('0');
        return;
    }
    while (val > 0) {
        buf[i++] = '0' + (val % 10);
        val /= 10;
    }
    while (--i >= 0) {
        uart_putchar(buf[i]);
    }
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

static inline void nemu_trap(uint64_t exit_code) {
    register uint64_t a0 __asm__("a0") = exit_code;
    __asm__ volatile(
        ".word 0x0000006b\n"
        :
        : "r"(a0)
    );
}

int main(void) {
    int rc;
    int ok;
    uint64_t start = rdcycle();
    rc = WORKLOAD_ENTRY(0, 0);
    uint64_t end = rdcycle();

    dummy();
    ok = (rc == 0) && workload_verify();
    uart_puts("KC=");
    uart_print_u64(end - start);
    uart_putchar('\n');
    uart_puts(ok ? "PASSED\n" : "FAILED\n");
    nemu_trap(ok ? 0 : 1);
    while (1) {
    }
    return 0;
}
