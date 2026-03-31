#ifndef TSVC_MEASURE_HDR
#define TSVC_MEASURE_HDR

#ifdef TSVC_MEASURE_CYCLES
#include <inttypes.h>
#include <sys/time.h>

static inline uint64_t tsvc_rdcycle(void) {
    uint64_t c;
    __asm__ volatile("rdcycle %0" : "=r"(c));
    return c;
}

static inline int tsvc_fake_gettimeofday(struct timeval* tv, void* tz) {
    (void)tz;
    tv->tv_sec = 0;
    tv->tv_usec = (suseconds_t)tsvc_rdcycle();
    return 0;
}

#define gettimeofday(tv, tz) tsvc_fake_gettimeofday((tv), (tz))
#endif

#endif
