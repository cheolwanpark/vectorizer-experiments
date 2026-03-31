#ifndef TSVC_TYPES_H
#define TSVC_TYPES_H

#ifdef TSVC_NO_STDLIB
typedef __UINT64_TYPE__ uint64_t;
typedef __SIZE_TYPE__ size_t;
#else
#include <stdint.h>
#include <stddef.h>
#endif

#ifndef LEN_1D
#define LEN_1D 1000
#endif

#ifndef LEN_2D
#define LEN_2D 32
#endif

typedef float real_t;

#endif
