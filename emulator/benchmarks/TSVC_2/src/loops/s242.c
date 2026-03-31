#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s242(struct args_t * func_args)
{

//    node splitting

    struct{real_t a;real_t b;} * x = func_args->arg_info;
    real_t s1 = x->a;
    real_t s2 = x->b;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations/5; nl++) {
        for (int i = 1; i < LEN_1D; ++i) {
            a[i] = a[i - 1] + s1 + s2 + b[i] + c[i] + d[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s242"; }

real_t tsvc_entry(struct args_t *func_args) { return s242(func_args); }

void *tsvc_prepare_args(void) {
    static struct {real_t a; real_t b;} args;
    args.a = tsvc_s1;
    args.b = tsvc_s2;
    return &args;
}
