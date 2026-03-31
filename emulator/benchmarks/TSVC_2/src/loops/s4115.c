#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s4115(struct args_t * func_args)
{

//    indirect addressing
//    sparse dot product
//    gather is required

    int * __restrict__ ip = func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t sum;
    for (int nl = 0; nl < iterations; nl++) {
        sum = 0.;
        for (int i = 0; i < LEN_1D; i++) {
            sum += a[i] * b[ip[i]];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return sum;
}

const char *tsvc_loop_name(void) { return "s4115"; }

real_t tsvc_entry(struct args_t *func_args) { return s4115(func_args); }

void *tsvc_prepare_args(void) {
    return tsvc_ip;
}
