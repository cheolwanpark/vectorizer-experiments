#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s276(struct args_t * func_args)
{

//    control flow
//    if test using loop index

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int mid = (LEN_1D/2);
    for (int nl = 0; nl < 4*iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            if (i+1 < mid) {
                a[i] += b[i] * c[i];
            } else {
                a[i] += b[i] * d[i];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s276"; }

real_t tsvc_entry(struct args_t *func_args) { return s276(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
