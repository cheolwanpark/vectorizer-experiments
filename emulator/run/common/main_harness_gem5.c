#include "types.h"

#ifndef WORKLOAD_ENTRY
#define WORKLOAD_ENTRY workload_main
#endif

extern int WORKLOAD_ENTRY(int argc, char **argv);

static inline uint64_t rdcycle(void) {
    uint64_t value;
    __asm__ volatile("rdcycle %0" : "=r"(value));
    return value;
}

static inline long syscall3(long n, long a0, long a1, long a2) {
    register long x10 __asm__("a0") = a0;
    register long x11 __asm__("a1") = a1;
    register long x12 __asm__("a2") = a2;
    register long x17 __asm__("a7") = n;

    __asm__ volatile("ecall"
                     : "+r"(x10)
                     : "r"(x11), "r"(x12), "r"(x17)
                     : "memory");
    return x10;
}

static void write_str(const char *s, size_t len) {
    (void)syscall3(64, 1, (long)s, (long)len);
}

static void write_dec(uint64_t value) {
    char buf[32];
    int pos = 30;

    buf[31] = '\0';
    if (value == 0) {
        buf[pos--] = '0';
    } else {
        while (value > 0 && pos >= 0) {
            buf[pos--] = '0' + (value % 10);
            value /= 10;
        }
    }

    write_str(&buf[pos + 1], 30 - pos);
}

int main(void) {
    static const char passed[] = "PASSED\n";
    static const char cycles_prefix[] = "cycles=";
    uint64_t start = rdcycle();
    int rc = WORKLOAD_ENTRY(0, 0);
    uint64_t end = rdcycle();

    write_str(cycles_prefix, sizeof(cycles_prefix) - 1);
    write_dec(end - start);
    write_str("\n", 1);
    if (rc == 0) {
        write_str(passed, sizeof(passed) - 1);
    }
    return rc;
}
