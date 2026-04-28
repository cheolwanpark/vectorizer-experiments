#ifndef TSVC_EMULATE_STDIO_H
#define TSVC_EMULATE_STDIO_H

#include <stdarg.h>

typedef struct tsvc_emulate_file FILE;

extern FILE *stderr;

int printf(const char *fmt, ...);
int fprintf(FILE *stream, const char *fmt, ...);
void perror(const char *msg);

#endif
