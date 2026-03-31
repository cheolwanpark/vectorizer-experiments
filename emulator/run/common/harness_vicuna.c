/**
 * Vicuna Simulation Harness
 *
 * Key characteristics:
 * - UART at 0xFF000000 (data), 0xFF000004 (status)
 * - 32-bit mcycle CSR for timing
 * - Integer-only vectors (Zve32x, no FP)
 * - Termination handled by CRT (jr x0)
 */
#include "types.h"

extern void kernel(void);
extern void init_arrays(void);

/* Vicuna UART addresses */
#define VICUNA_UART_DATA   (*(volatile unsigned int *)0xFF000000)
#define VICUNA_UART_STATUS (*(volatile unsigned int *)0xFF000004)

static inline unsigned int rdcycle(void) {
    unsigned int c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

static void uart_putc(char ch) {
    /* Wait until transmitter ready (status bit 0 = 0) */
    while (VICUNA_UART_STATUS & 1)
        ;
    VICUNA_UART_DATA = (unsigned int)ch;
}

static void print_str(const char *s) {
    while (*s)
        uart_putc(*s++);
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

/* Store cycles in a known location for potential extraction */
volatile unsigned int measured_cycles __attribute__((section(".data")));

int main(void) {
    /* Warmup run */
    init_arrays();
    kernel();
    dummy();

    /* Timed run */
    init_arrays();
    unsigned int start = rdcycle();
    kernel();
    unsigned int end = rdcycle();
    dummy();

    measured_cycles = end - start;

    /* Print result via UART */
    print_str("cycles=");
    print_dec(end - start);
    print_str("\n");

    /* Return - CRT will handle termination via jr x0 */
    return 0;
}
