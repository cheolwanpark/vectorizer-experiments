#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../benchmarks/TSVC_2/src/common.h"
#include "../../benchmarks/TSVC_2/src/single_support.h"

int *tsvc_ip;
int tsvc_n1 = 1;
int tsvc_n3 = 1;
real_t tsvc_s1;
real_t tsvc_s2;

#define TSVC_HEAP_BYTES ((2 * LEN_1D * (int)(sizeof(real_t) + sizeof(int))) + 1024)

static unsigned char tsvc_heap[TSVC_HEAP_BYTES] __attribute__((aligned(64)));
static size_t tsvc_heap_offset;

FILE *stderr;

static uintptr_t align_up(uintptr_t value, size_t alignment) {
    uintptr_t mask;

    if (alignment == 0) {
        alignment = sizeof(void *);
    }
    mask = (uintptr_t)alignment - 1;
    return (value + mask) & ~mask;
}

void tsvc_emulate_reset_heap(void) {
    tsvc_heap_offset = 0;
}

void *memalign(size_t alignment, size_t size) {
    uintptr_t base;
    uintptr_t aligned;
    size_t next_offset;

    base = (uintptr_t)tsvc_heap + tsvc_heap_offset;
    aligned = align_up(base, alignment);
    next_offset = (size_t)(aligned - (uintptr_t)tsvc_heap) + size;
    if (next_offset > sizeof(tsvc_heap)) {
        return NULL;
    }
    tsvc_heap_offset = next_offset;
    return (void *)aligned;
}

int printf(const char *fmt, ...) {
    (void)fmt;
    return 0;
}

int fprintf(FILE *stream, const char *fmt, ...) {
    (void)stream;
    (void)fmt;
    return 0;
}

int strcmp(const char *lhs, const char *rhs) {
    while (*lhs != '\0' && *lhs == *rhs) {
        lhs++;
        rhs++;
    }
    return (unsigned char)*lhs - (unsigned char)*rhs;
}

void exit(int code) {
    (void)code;
    while (1) {
        __asm__ volatile("" ::: "memory");
    }
}
