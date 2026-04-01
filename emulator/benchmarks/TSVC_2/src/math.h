#ifndef TSVC_BAREMETAL_MATH_H
#define TSVC_BAREMETAL_MATH_H

/*
 * Minimal math compatibility header for TSVC bare-metal emulate builds.
 *
 * The XiangShan emulate toolchain path compiles TSVC sources with
 * -I.../TSVC_2/src but without a libc math header in the target sysroot.
 * TSVC currently only needs absolute-value helpers, so keep this shim small
 * and extend it intentionally if new math APIs are introduced.
 */

static inline float fabsf(float value) {
    return value < 0.0f ? -value : value;
}

static inline double fabs(double value) {
    return value < 0.0 ? -value : value;
}

#endif
