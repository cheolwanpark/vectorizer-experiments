#include <stdarg.h>
#include <stdint.h>

#include <pthread.h>
#include <stdio.h>

namespace std {
using ::ferror;
using ::feof;
using ::fread;
}

typedef struct {
    uint64_t checksum;
    int values_written;
} ParsecStreamclusterCaptureFile;

static ParsecStreamclusterCaptureFile parsec_streamcluster_capture_file;
static int parsec_streamcluster_verify_ok;

static uint64_t parsec_streamcluster_mix_u64(uint64_t checksum, uint64_t value) {
    return (checksum * 1315423911ULL) ^ value;
}

static FILE *parsec_streamcluster_fopen(const char *path, const char *mode) {
    (void)path;
    (void)mode;
    parsec_streamcluster_capture_file.checksum = 0;
    parsec_streamcluster_capture_file.values_written = 0;
    return (FILE *)&parsec_streamcluster_capture_file;
}

static int parsec_streamcluster_fclose(FILE *stream) {
    (void)stream;
    return 0;
}

static int parsec_streamcluster_fprintf(FILE *stream, const char *fmt, ...) {
    va_list args;

    if (stream == stderr) {
        return 0;
    }

    va_start(args, fmt);
    for (const char *cursor = fmt; *cursor != '\0'; ++cursor) {
        if (*cursor != '%') {
            continue;
        }
        ++cursor;
        if (*cursor == 'l' && cursor[1] == 'f') {
            union {
                double value;
                uint64_t bits;
            } payload;

            payload.value = va_arg(args, double);
            parsec_streamcluster_capture_file.checksum =
                parsec_streamcluster_mix_u64(parsec_streamcluster_capture_file.checksum, payload.bits);
            parsec_streamcluster_capture_file.values_written += 1;
            ++cursor;
            continue;
        }
        if (*cursor == 'u') {
            unsigned int value = va_arg(args, unsigned int);

            parsec_streamcluster_capture_file.checksum =
                parsec_streamcluster_mix_u64(parsec_streamcluster_capture_file.checksum, (uint64_t)value);
            parsec_streamcluster_capture_file.values_written += 1;
            continue;
        }
        if (*cursor == 'd' || *cursor == 'i') {
            int value = va_arg(args, int);

            parsec_streamcluster_capture_file.checksum =
                parsec_streamcluster_mix_u64(parsec_streamcluster_capture_file.checksum, (uint64_t)(uint32_t)value);
            parsec_streamcluster_capture_file.values_written += 1;
            continue;
        }
        if (*cursor == 's') {
            (void)va_arg(args, const char *);
            continue;
        }
    }
    va_end(args);
    return 0;
}

#define fopen parsec_streamcluster_fopen
#define fclose parsec_streamcluster_fclose
#define fprintf parsec_streamcluster_fprintf
#ifdef main
#define PARSEC_STREAMCLUSTER_RESTORE_MAIN 1
#undef main
#endif
#define main parsec_streamcluster_upstream_main
#include "../../../../../parsec-benchmark/pkgs/kernels/streamcluster/src/streamcluster.cpp"
#undef main
#undef fprintf
#undef fclose
#undef fopen

int workload_verify(void) {
    return parsec_streamcluster_verify_ok;
}

#ifdef PARSEC_STREAMCLUSTER_RESTORE_MAIN
#define main workload_main
#endif
int main(int argc, char **argv) {
    static char program[] = "streamcluster";
    static char kmin[] = "10";
    static char kmax[] = "20";
    static char dim[] = "8";
    static char npoints[] = "4096";
    static char chunksize[] = "256";
    static char clustersize[] = "512";
    static char infile[] = "parsec:streamcluster:input";
    static char outfile[] = "parsec:streamcluster:output";
    static char threads[] = "1";
    char *default_argv[] = {
        program,
        kmin,
        kmax,
        dim,
        npoints,
        chunksize,
        clustersize,
        infile,
        outfile,
        threads,
        NULL,
    };
    int rc;

    (void)argc;
    (void)argv;

    rc = parsec_streamcluster_upstream_main(10, default_argv);
    parsec_streamcluster_verify_ok =
        (rc == 0) &&
        (parsec_streamcluster_capture_file.values_written > 0) &&
        (parsec_streamcluster_capture_file.checksum != 0);
    return rc;
}
