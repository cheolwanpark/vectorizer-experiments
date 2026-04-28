#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    float s;
    float strike;
    float r;
    float divq;
    float v;
    float t;
    const char *option_type;
    float divs;
    float ref_value;
} ParsecBlackscholesSeed;

#define PARSEC_BLACKSCHOLES_SEED_COUNT 1000
#define PARSEC_BLACKSCHOLES_DEFAULT_OPTIONS 1024

static const ParsecBlackscholesSeed parsec_blackscholes_seed[] = {
#include "../../../../../parsec-benchmark/pkgs/apps/blackscholes/src/optionData.txt"
};

typedef struct {
    size_t row_index;
    int mode;
} ParsecBlackscholesFile;

static ParsecBlackscholesFile parsec_blackscholes_input_file;
static ParsecBlackscholesFile parsec_blackscholes_output_file;
static int parsec_blackscholes_verify_ok;

static FILE *parsec_blackscholes_fopen(const char *path, const char *mode) {
    (void)path;
    if (mode != NULL && mode[0] == 'r') {
        parsec_blackscholes_input_file.row_index = 0;
        parsec_blackscholes_input_file.mode = 0;
        return (FILE *)&parsec_blackscholes_input_file;
    }
    parsec_blackscholes_output_file.row_index = 0;
    parsec_blackscholes_output_file.mode = 1;
    return (FILE *)&parsec_blackscholes_output_file;
}

static int parsec_blackscholes_fclose(FILE *stream) {
    (void)stream;
    return 0;
}

static int parsec_blackscholes_fscanf(FILE *stream, const char *fmt, ...) {
    ParsecBlackscholesFile *file = (ParsecBlackscholesFile *)stream;
    va_list args;

    if (file == NULL || fmt == NULL) {
        return 0;
    }

    va_start(args, fmt);
    if (fmt[0] == '%' && fmt[1] == 'i') {
        int *num_options = va_arg(args, int *);

        *num_options = PARSEC_BLACKSCHOLES_DEFAULT_OPTIONS;
        va_end(args);
        return 1;
    }

    if (strstr(fmt, "%f %f %f %f %f %f %c %f %f") != NULL) {
        const ParsecBlackscholesSeed *seed =
            &parsec_blackscholes_seed[file->row_index % PARSEC_BLACKSCHOLES_SEED_COUNT];
        float *s = va_arg(args, float *);
        float *strike = va_arg(args, float *);
        float *rate = va_arg(args, float *);
        float *divq = va_arg(args, float *);
        float *volatility = va_arg(args, float *);
        float *time = va_arg(args, float *);
        char *option_type = va_arg(args, char *);
        float *divs = va_arg(args, float *);
        float *ref_value = va_arg(args, float *);

        *s = seed->s;
        *strike = seed->strike;
        *rate = seed->r;
        *divq = seed->divq;
        *volatility = seed->v;
        *time = seed->t;
        *option_type = seed->option_type[0];
        *divs = seed->divs;
        *ref_value = seed->ref_value;
        file->row_index += 1;
        va_end(args);
        return 9;
    }

    va_end(args);
    return 0;
}

#define fopen parsec_blackscholes_fopen
#define fclose parsec_blackscholes_fclose
#define fscanf parsec_blackscholes_fscanf
#ifdef main
#define PARSEC_BLACKSCHOLES_RESTORE_MAIN 1
#undef main
#endif
#define main parsec_blackscholes_upstream_main
#include "../../../../../parsec-benchmark/pkgs/apps/blackscholes/src/blackscholes.c"
#undef main
#undef fscanf
#undef fclose
#undef fopen

int workload_verify(void) {
    return parsec_blackscholes_verify_ok;
}

#ifdef PARSEC_BLACKSCHOLES_RESTORE_MAIN
#define main workload_main
#endif
int main(int argc, char **argv) {
    static char program[] = "blackscholes";
    static char threads[] = "1";
    static char input[] = "parsec:blackscholes:input";
    static char output[] = "parsec:blackscholes:output";
    char *default_argv[] = {program, threads, input, output, NULL};
    int rc;
    int mismatches = 0;

    (void)argc;
    (void)argv;

    rc = parsec_blackscholes_upstream_main(4, default_argv);
    for (int i = 0; i < numOptions; ++i) {
        float delta = prices[i] - data[i].DGrefval;

        if (delta < 0.0f) {
            delta = -delta;
        }
        if (delta > 2.5e-2f) {
            mismatches += 1;
        }
    }
    parsec_blackscholes_verify_ok =
        (rc == 0) &&
        (nThreads == 1) &&
        (numOptions == PARSEC_BLACKSCHOLES_DEFAULT_OPTIONS) &&
        (mismatches == 0);
    return rc;
}
