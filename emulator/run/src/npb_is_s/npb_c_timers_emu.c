#include <stdint.h>

static double start_time[64];
static double elapsed_time[64];

static inline uint64_t rdcycle64(void) {
    uint64_t value;
    __asm__ volatile("csrr %0, mcycle" : "=r"(value));
    return value;
}

static double cycle_now(void) {
    return (double)rdcycle64();
}

void timer_clear(int n) {
    elapsed_time[n] = 0.0;
}

void timer_start(int n) {
    start_time[n] = cycle_now();
}

void timer_stop(int n) {
    elapsed_time[n] += cycle_now() - start_time[n];
}

double timer_read(int n) {
    return elapsed_time[n];
}

int check_timer_flag(void) {
    return 0;
}
