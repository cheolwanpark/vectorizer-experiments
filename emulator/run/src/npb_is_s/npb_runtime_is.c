#include <stddef.h>
#include <stdint.h>

#define NPB_IS_HEAP_BYTES 65536

typedef struct npb_emulate_file FILE;

FILE *stderr;

static unsigned char npb_is_heap[NPB_IS_HEAP_BYTES] __attribute__((aligned(16)));
static size_t npb_is_heap_offset;

static uintptr_t align_up(uintptr_t value, size_t alignment) {
    uintptr_t mask = (uintptr_t)alignment - 1;
    return (value + mask) & ~mask;
}

void *malloc(size_t size) {
    uintptr_t base;
    uintptr_t aligned;
    size_t next_offset;

    if (size == 0) {
        size = 1;
    }
    base = (uintptr_t)npb_is_heap + npb_is_heap_offset;
    aligned = align_up(base, 16);
    next_offset = (size_t)(aligned - (uintptr_t)npb_is_heap) + size;
    if (next_offset > sizeof(npb_is_heap)) {
        return (void *)0;
    }
    npb_is_heap_offset = next_offset;
    return (void *)aligned;
}

void free(void *ptr) {
    (void)ptr;
}

char *getenv(const char *name) {
    (void)name;
    return (char *)0;
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

void perror(const char *msg) {
    (void)msg;
}

void exit(int code) {
    (void)code;
    while (1) {
        __asm__ volatile("" ::: "memory");
    }
}
