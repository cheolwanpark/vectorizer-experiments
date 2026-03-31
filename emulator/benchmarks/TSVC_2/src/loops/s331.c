#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s331(struct args_t * func_args)
{

//    search loops
//    if to last-1

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int j;
    real_t chksum;
    for (int nl = 0; nl < iterations; nl++) {
        j = -1;
        for (int i = 0; i < LEN_1D; i++) {
            if (a[i] < (real_t)0.) {
                j = i;
            }
        }
        chksum = (real_t) j;
        dummy(a, b, c, d, e, aa, bb, cc, chksum);
    }

    gettimeofday(&func_args->t2, NULL);
    return j+1;
}

const char *tsvc_loop_name(void) { return "s331"; }

real_t tsvc_entry(struct args_t *func_args) { return s331(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
