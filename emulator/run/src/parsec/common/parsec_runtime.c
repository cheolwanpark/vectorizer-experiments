#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>

#include "stdio.h"
#include "stdlib.h"
#include "string.h"

#define PARSEC_HEAP_BYTES (32 * 1024 * 1024)

struct tsvc_emulate_file {
    int error;
    int eof;
};

static unsigned char parsec_heap[PARSEC_HEAP_BYTES] __attribute__((aligned(64)));
static size_t parsec_heap_offset;
static uint64_t parsec_rand48_state = 0x330eULL;
static struct tsvc_emulate_file parsec_stderr_file;
static struct tsvc_emulate_file parsec_dummy_file;

FILE *stderr = &parsec_stderr_file;

static uintptr_t align_up(uintptr_t value, size_t alignment) {
    uintptr_t mask;

    if (alignment == 0) {
        alignment = sizeof(void *);
    }
    mask = (uintptr_t)alignment - 1;
    return (value + mask) & ~mask;
}

void parsec_assert_fail(void) {
    while (1) {
        __asm__ volatile("" ::: "memory");
    }
}

void *malloc(size_t size) {
    uintptr_t base;
    uintptr_t aligned;
    size_t next_offset;

    if (size == 0) {
        size = 1;
    }
    base = (uintptr_t)parsec_heap + parsec_heap_offset;
    aligned = align_up(base, 16);
    next_offset = (size_t)(aligned - (uintptr_t)parsec_heap) + size;
    if (next_offset > sizeof(parsec_heap)) {
        return NULL;
    }
    parsec_heap_offset = next_offset;
    return (void *)aligned;
}

void *calloc(size_t count, size_t size) {
    unsigned char *ptr;
    size_t total = count * size;

    ptr = (unsigned char *)malloc(total);
    if (ptr == NULL) {
        return NULL;
    }
    memset(ptr, 0, total);
    return ptr;
}

void *realloc(void *ptr, size_t size) {
    void *next;

    if (ptr == NULL) {
        return malloc(size);
    }
    if (size == 0) {
        return ptr;
    }
    next = malloc(size);
    if (next == NULL) {
        return NULL;
    }
    return next;
}

void free(void *ptr) {
    (void)ptr;
}

int atoi(const char *text) {
    int sign = 1;
    int value = 0;

    if (text == NULL) {
        return 0;
    }
    while (*text == ' ' || *text == '\t' || *text == '\n') {
        text++;
    }
    if (*text == '-') {
        sign = -1;
        text++;
    } else if (*text == '+') {
        text++;
    }
    while (*text >= '0' && *text <= '9') {
        value = (value * 10) + (*text - '0');
        text++;
    }
    return sign * value;
}

size_t strlen(const char *text) {
    size_t len = 0;

    if (text == NULL) {
        return 0;
    }
    while (text[len] != '\0') {
        len++;
    }
    return len;
}

int strcmp(const char *lhs, const char *rhs) {
    while (*lhs != '\0' && *lhs == *rhs) {
        lhs++;
        rhs++;
    }
    return (unsigned char)*lhs - (unsigned char)*rhs;
}

char *strcpy(char *dst, const char *src) {
    char *cursor = dst;

    while (*src != '\0') {
        *cursor++ = *src++;
    }
    *cursor = '\0';
    return dst;
}

char *strstr(const char *haystack, const char *needle) {
    size_t needle_len;

    if (haystack == NULL || needle == NULL) {
        return NULL;
    }
    needle_len = strlen(needle);
    if (needle_len == 0) {
        return (char *)haystack;
    }
    for (; *haystack != '\0'; ++haystack) {
        size_t i = 0;

        while (needle[i] != '\0' && haystack[i] == needle[i]) {
            i++;
        }
        if (i == needle_len) {
            return (char *)haystack;
        }
    }
    return NULL;
}

void *memcpy(void *dst, const void *src, size_t count) {
    unsigned char *out = (unsigned char *)dst;
    const unsigned char *in = (const unsigned char *)src;

    for (size_t i = 0; i < count; ++i) {
        out[i] = in[i];
    }
    return dst;
}

void *memset(void *dst, int value, size_t count) {
    unsigned char *out = (unsigned char *)dst;

    for (size_t i = 0; i < count; ++i) {
        out[i] = (unsigned char)value;
    }
    return dst;
}

void srand48(long seed) {
    parsec_rand48_state = (((uint64_t)seed) << 16) | 0x330eULL;
}

long lrand48(void) {
    parsec_rand48_state = (0x5deece66dULL * parsec_rand48_state + 0xbULL) & ((1ULL << 48) - 1ULL);
    return (long)(parsec_rand48_state >> 17);
}

double drand48(void) {
    return (double)lrand48() / (double)0x7fffffff;
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

int fscanf(FILE *stream, const char *fmt, ...) {
    (void)stream;
    (void)fmt;
    return 0;
}

int fflush(FILE *stream) {
    (void)stream;
    return 0;
}

FILE *fopen(const char *path, const char *mode) {
    (void)path;
    (void)mode;
    parsec_dummy_file.error = 0;
    parsec_dummy_file.eof = 0;
    return &parsec_dummy_file;
}

int fclose(FILE *stream) {
    (void)stream;
    return 0;
}

size_t fread(void *ptr, size_t size, size_t count, FILE *stream) {
    (void)ptr;
    (void)size;
    (void)count;
    (void)stream;
    return 0;
}

size_t fwrite(const void *ptr, size_t size, size_t count, FILE *stream) {
    (void)ptr;
    (void)size;
    (void)stream;
    return count;
}

int ferror(FILE *stream) {
    return stream ? stream->error : 0;
}

int feof(FILE *stream) {
    return stream ? stream->eof : 1;
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
