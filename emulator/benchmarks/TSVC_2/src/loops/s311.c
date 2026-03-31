#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s311(struct args_t * func_args)
{

//    reductions
//    sum reduction

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t sum;
    for (int nl = 0; nl < iterations*10; nl++) {
        sum = (real_t)0.;
        for (int i = 0; i < LEN_1D; i++) {
            sum += a[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, sum);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s311"; }

real_t tsvc_entry(struct args_t *func_args) { return s311(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
