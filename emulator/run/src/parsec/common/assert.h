#ifndef PARSEC_BAREMETAL_ASSERT_H
#define PARSEC_BAREMETAL_ASSERT_H

#ifdef __cplusplus
extern "C" {
#endif

void parsec_assert_fail(void);

#ifdef __cplusplus
}
#endif

#define assert(expr) do { \
    if (!(expr)) { \
        parsec_assert_fail(); \
    } \
} while (0)

#endif
