#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"

void s152s(real_t a[LEN_1D], real_t b[LEN_1D], real_t c[LEN_1D], int i)
{
    a[i] += b[i] * c[i];
}

real_t s152(struct args_t * func_args)
{

//    interprocedural data flow analysis
//    collecting information from a subroutine

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    for (int nl = 0; nl < iterations; nl++) {
        for (int i = 0; i < LEN_1D; i++) {
            b[i] = d[i] * e[i];
            s152s(a, b, c, i);
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s152"; }

real_t tsvc_entry(struct args_t *func_args) { return s152(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
