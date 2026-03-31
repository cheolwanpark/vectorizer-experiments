#ifndef TSVC_COMMON_HDR
#define TSVC_COMMON_HDR

#ifndef iterations
#define iterations 100000
#endif
#ifndef LEN_1D
#define LEN_1D 32000
#endif
#ifndef LEN_2D
#define LEN_2D 256
#endif

#include <sys/time.h>
#include <stdlib.h>

struct args_t {
    struct timeval t1;
    struct timeval t2;
    void * __restrict__ arg_info;
};

#if 0
typedef double real_t;
#define ABS fabs
#else
typedef float real_t;
#define ABS fabsf
#endif

int dummy(real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_1D], real_t[LEN_2D][LEN_2D], real_t[LEN_2D][LEN_2D], real_t[LEN_2D][LEN_2D], real_t);

void init(int** ip, real_t* s1, real_t* s2);

int initialise_arrays(const char* name);
real_t calc_checksum(const char * name);
real_t test(real_t* A);
real_t f(real_t a, real_t b);

#endif
