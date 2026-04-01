#ifndef TSVC_BAREMETAL_INTTYPES_H
#define TSVC_BAREMETAL_INTTYPES_H

/*
 * Minimal inttypes compatibility header for TSVC bare-metal emulate builds.
 *
 * TSVC only needs uint64_t for the cycle-based measurement shim.
 */

typedef __UINT64_TYPE__ uint64_t;

#endif
