#include "types.h"
#include "arrays.h"

extern void kernel(void);

static inline uint32_t rdcycle(void) {
    uint32_t c;
    __asm__ volatile("csrr %0, mcycle" : "=r"(c));
    return c;
}

/* T1 uses memory-mapped UART at 0x10000000 for output */
#define UART_BASE 0x10000000
#define UART_TX   (*(volatile uint32_t *)(UART_BASE + 0))

static void print_char(char ch) {
    UART_TX = ch;
}

static void print_str(const char *s) {
    while (*s) print_char(*s++);
}

static void print_dec(uint32_t n) {
    char buf[12];
    int i = 10;
    buf[11] = '\0';
    if (n == 0) buf[i--] = '0';
    else while (n > 0) { buf[i--] = '0' + (n % 10); n /= 10; }
    print_str(&buf[i + 1]);
}

__attribute__((noinline))
static void dummy(void) {
    __asm__ volatile("" ::: "memory");
}

/* T1 expects 'test' as the entry point, not 'main' */
void test(void) {
    init_arrays();
    kernel();
    dummy();

    init_arrays();
    uint32_t start = rdcycle();
    kernel();
    uint32_t end = rdcycle();
    dummy();

    print_str("cycles=");
    print_dec(end - start);
    print_str("\n");
}
