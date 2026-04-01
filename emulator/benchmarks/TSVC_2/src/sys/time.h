#ifndef TSVC_BAREMETAL_SYS_TIME_H
#define TSVC_BAREMETAL_SYS_TIME_H

/*
 * Minimal sys/time compatibility header for TSVC bare-metal emulate builds.
 *
 * TSVC only needs struct timeval so the cycle-based measurement shim can
 * populate timestamps without depending on a full target libc.
 */

typedef long time_t;
typedef long suseconds_t;

struct timeval {
    time_t tv_sec;
    suseconds_t tv_usec;
};

#endif
