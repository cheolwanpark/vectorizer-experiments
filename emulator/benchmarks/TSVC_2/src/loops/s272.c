#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s272(struct args_t * func_args)
{

//    control flow
//    loop with independent conditional

    int t = *(int*)func_args->arg_info;

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (e[i] >= t) {
                a[i] += c[i] * d[i];
                b[i] += c[i] * c[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s272"; }

real_t tsvc_entry(struct args_t *func_args) { return s272(func_args); }

void *tsvc_prepare_args(void) {
    return &tsvc_s1;
}
