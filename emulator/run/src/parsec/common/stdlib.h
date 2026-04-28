#ifndef PARSEC_BAREMETAL_STDLIB_H
#define PARSEC_BAREMETAL_STDLIB_H

#include <stddef.h>

void *malloc(size_t size);
void *calloc(size_t count, size_t size);
void *realloc(void *ptr, size_t size);
void free(void *ptr);
int atoi(const char *text);
void srand48(long seed);
long lrand48(void);
double drand48(void);
void exit(int code);

#endif
