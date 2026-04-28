#ifndef PARSEC_BAREMETAL_STRING_H
#define PARSEC_BAREMETAL_STRING_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

size_t strlen(const char *text);
int strcmp(const char *lhs, const char *rhs);
char *strcpy(char *dst, const char *src);
char *strstr(const char *haystack, const char *needle);
void *memcpy(void *dst, const void *src, size_t count);
void *memset(void *dst, int value, size_t count);

#ifdef __cplusplus
}
#endif

#endif
