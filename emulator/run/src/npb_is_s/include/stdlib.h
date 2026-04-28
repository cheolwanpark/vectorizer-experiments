#ifndef NPB_EMU_STDLIB_H
#define NPB_EMU_STDLIB_H

typedef __SIZE_TYPE__ size_t;

#ifndef NULL
#define NULL ((void *)0)
#endif

void *malloc(size_t size);
void free(void *ptr);
char *getenv(const char *name);
void exit(int code);

#endif
