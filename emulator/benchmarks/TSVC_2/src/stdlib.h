#ifndef TSVC_BAREMETAL_STDLIB_H
#define TSVC_BAREMETAL_STDLIB_H

#include <stddef.h>

/*
 * Minimal stdlib compatibility header for TSVC bare-metal emulate builds.
 *
 * TSVC only needs NULL and an exit declaration in the currently failing
 * emulate path.
 */

void exit(int code);

#endif
