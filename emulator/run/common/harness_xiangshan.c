/**
 * XiangShan Simulation Harness
 *
 * Uses nemu_trap instruction for proper termination with XiangShan's difftest.
 * nemu_trap opcode: 0x0000006b (when a0=0, signals successful exit)
 * Kernel cycles are output via UART (0x40600004) as "KC=<cycles>\n".
 */
#include "types.h"
#include "arrays.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY kernel
#endif

extern void WORKLOAD_ENTRY(void);

/* XiangShan UART TX register (AXI4UART at 0x40600000, TX offset 0x4) */
#define UART_TX (*(volatile uint8_t *)0x40600004UL)

static void uart_putchar(char c) {
    UART_TX = (uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) uart_putchar(*s++);
}

static void uart_print_u64(uint64_t val) {
    char buf[20];
    int i = 0;
    if (val == 0) { uart_putchar('0'); return; }
    while (val > 0) { buf[i++] = '0' + (val % 10); val /= 10; }
    while (--i >= 0) uart_putchar(buf[i]);
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

/* nemu_trap: triggers NEMU to exit simulation
 * a0 = 0: success (GOOD_TRAP)
 * a0 != 0: failure
 */
static inline void nemu_trap(uint64_t exit_code) {
    register uint64_t a0 __asm__("a0") = exit_code;
    __asm__ volatile(
        ".word 0x0000006b\n"  /* nemu_trap instruction */
        :
        : "r"(a0)
    );
}

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

    uint64_t kernel_cycles = end - start;

    /* Output kernel cycles via UART */
    uart_puts("KC=");
    uart_print_u64(kernel_cycles);
    uart_putchar('\n');

    /* Signal successful completion via nemu_trap */
    nemu_trap(0);

    /* Should never reach here */
    while (1);
    return 0;
}
