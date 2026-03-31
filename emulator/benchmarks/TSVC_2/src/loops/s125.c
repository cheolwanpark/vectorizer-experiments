#include <math.h>
#include "../common.h"
#include "../array_defs.h"
#include "../single_support.h"
#include "../tsvc_measure.h"


real_t s125(struct args_t * func_args)
{

//    induction variable recognition
//    induction variable in two loops; collapsing possible

    initialise_arrays(__func__);
    gettimeofday(&func_args->t1, NULL);

    int k;
    for (int nl = 0; nl < 100*(iterations/(LEN_2D)); nl++) {
        k = -1;
        for (int i = 0; i < LEN_2D; i++) {
            for (int j = 0; j < LEN_2D; j++) {
                k++;
                flat_2d_array[k] = aa[i][j] + bb[i][j] * cc[i][j];
            }
        }
        dummy(a, b, c, d, e, aa, bb, cc, 0.);
    }

    gettimeofday(&func_args->t2, NULL);
    return calc_checksum(__func__);
}

const char *tsvc_loop_name(void) { return "s125"; }

real_t tsvc_entry(struct args_t *func_args) { return s125(func_args); }

void *tsvc_prepare_args(void) {
    return NULL;
}
