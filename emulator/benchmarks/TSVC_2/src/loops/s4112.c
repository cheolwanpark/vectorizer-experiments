#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s4112(struct args_t * func_args)
{

//    indirect addressing
//    sparse saxpy
//    gather is required

    struct{int * __restrict__ a;real_t b;} * x = func_args->arg_info;
    int * __restrict__ ip = x->a;
    real_t s = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            a[i] += b[ip[i]] * s;
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s4112"; }

real_t tsvc_entry(struct args_t *func_args) { return s4112(func_args); }

void *tsvc_prepare_args(void) {
    static struct {int *a; real_t b;} args;
    args.a = tsvc_ip;
    args.b = tsvc_s1;
    return &args;
}
