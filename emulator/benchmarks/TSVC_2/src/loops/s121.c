#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s121(struct args_t * func_args)
{

//    induction variable recognition
//    loop with possible ambiguity because of scalar store

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int j;
    for (int nl = 0; nl < 3*iterations; nl++) {
        for (int i = 0; i < LEN_1D-1; i++) {
            j = i + 1;
            a[i] = a[j] + b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s121"; }

real_t tsvc_entry(struct args_t *func_args) { return s121(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
