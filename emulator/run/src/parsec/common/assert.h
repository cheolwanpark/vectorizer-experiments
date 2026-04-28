#ifndef PARSEC_BAREMETAL_ASSERT_H
#define PARSEC_BAREMETAL_ASSERT_H

void parsec_assert_fail(void);

#define assert(expr) do { \
    if (!(expr)) { \
        parsec_assert_fail(); \
    } \
} while (0)

#endif
