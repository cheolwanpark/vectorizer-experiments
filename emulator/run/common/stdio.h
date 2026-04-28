#ifndef TSVC_EMULATE_STDIO_H
#define TSVC_EMULATE_STDIO_H

#include <stdarg.h>
#include <stddef.h>

typedef struct tsvc_emulate_file FILE;

#ifdef __cplusplus
extern "C" {
#endif

extern FILE *stderr;

int printf(const char *fmt, ...);
int fprintf(FILE *stream, const char *fmt, ...);
int fscanf(FILE *stream, const char *fmt, ...);
int fflush(FILE *stream);
FILE *fopen(const char *path, const char *mode);
int fclose(FILE *stream);
size_t fread(void *ptr, size_t size, size_t count, FILE *stream);
size_t fwrite(const void *ptr, size_t size, size_t count, FILE *stream);
int ferror(FILE *stream);
int feof(FILE *stream);
void perror(const char *msg);

#ifdef __cplusplus
}
#endif

#endif
