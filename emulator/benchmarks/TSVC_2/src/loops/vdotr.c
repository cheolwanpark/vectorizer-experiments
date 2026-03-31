#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t vdotr(struct args_t * func_args)
{

//    control loops
//    vector dot product reduction

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    real_t dot;
    for (int nl = 0; nl < iterations*10; nl++) {
        dot = 0.;
        for (int i = 0; i < LEN_1D; i++) {
            dot += a[i] * b[i];
        }
        dummy(a, b, c, d, e, aa, bb, cc, dot);
    }

    gettimeofday(&func_args->t2, NULL);
    return dot;
}

const char *tsvc_loop_name(void) { return "vdotr"; }

real_t tsvc_entry(struct args_t *func_args) { return vdotr(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
