#include <stdint.h>

static int parsec_swaptions_verify_ok;
static double parsec_swaptions_price_sum;
static double parsec_swaptions_error_sum;

#ifdef main
#define PARSEC_SWAPTIONS_RESTORE_MAIN 1
#undef main
#endif
#define main parsec_swaptions_upstream_main
#include "upstream/HJM_Securities.cpp"
#undef main

int workload_verify(void) {
    return parsec_swaptions_verify_ok;
}

#ifdef PARSEC_SWAPTIONS_RESTORE_MAIN
#define main workload_main
#endif
int main(int argc, char **argv) {
    static char program[] = "swaptions";
    static char opt_sm[] = "-sm";
    static char trials[] = "256";
    static char opt_nt[] = "-nt";
    static char threads[] = "1";
    static char opt_ns[] = "-ns";
    static char swaptions_count[] = "16";
    static char opt_sd[] = "-sd";
    static char seed_text[] = "1";
    char *default_argv[] = {
        program,
        opt_sm,
        trials,
        opt_nt,
        threads,
        opt_ns,
        swaptions_count,
        opt_sd,
        seed_text,
        NULL,
    };
    int rc;

    (void)argc;
    (void)argv;

    rc = parsec_swaptions_upstream_main(9, default_argv);
    parsec_swaptions_price_sum = 0.0;
    parsec_swaptions_error_sum = 0.0;
    for (int i = 0; i < nSwaptions; ++i) {
        parsec_swaptions_price_sum += swaptions[i].dSimSwaptionMeanPrice;
        parsec_swaptions_error_sum += swaptions[i].dSimSwaptionStdError;
    }
    parsec_swaptions_verify_ok =
        (rc == 0) &&
        (nThreads == 1) &&
        (nSwaptions == 16) &&
        (NUM_TRIALS == 256) &&
        (parsec_swaptions_price_sum == parsec_swaptions_price_sum) &&
        (parsec_swaptions_error_sum == parsec_swaptions_error_sum) &&
        (parsec_swaptions_price_sum > 0.0) &&
        (parsec_swaptions_error_sum >= 0.0);
    return rc;
}
