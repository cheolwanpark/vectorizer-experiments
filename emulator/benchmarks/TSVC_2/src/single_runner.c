#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

#include "common.h"
#include "array_defs.h"
#include "single_support.h"
#include "tsvc_measure.h"

typedef real_t (*test_function_t)(struct args_t *);

int *tsvc_ip;
int tsvc_n1 = 1;
int tsvc_n3 = 1;
real_t tsvc_s1;
real_t tsvc_s2;

static void time_function(test_function_t vector_func, void *arg_info) {
    struct args_t func_args = {.arg_info = arg_info};

    double result = vector_func(&func_args);

#ifdef TSVC_MEASURE_CYCLES
    uint64_t start = (uint64_t)func_args.t1.tv_usec;
    uint64_t end = (uint64_t)func_args.t2.tv_usec;
    uint64_t taken = end - start;
    printf("%10" PRIu64 "\t%f\n", taken, result);
#else
    double tic = func_args.t1.tv_sec + (func_args.t1.tv_usec / 1000000.0);
    double toc = func_args.t2.tv_sec + (func_args.t2.tv_usec / 1000000.0);
    double taken = toc - tic;
    printf("%10.3f\t%f\n", taken, result);
#endif
}

int main(void) {
    init(&tsvc_ip, &tsvc_s1, &tsvc_s2);

    printf("Loop \tTime(sec) \tChecksum\n");

    time_function(tsvc_entry, tsvc_prepare_args());

    return EXIT_SUCCESS;
}
