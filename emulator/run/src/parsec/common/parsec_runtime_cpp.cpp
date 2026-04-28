#include "assert.h"
#include "stdlib.h"

void *operator new(size_t size) {
    return malloc(size);
}

void *operator new[](size_t size) {
    return malloc(size);
}

void operator delete(void *ptr) noexcept {
    free(ptr);
}

void operator delete[](void *ptr) noexcept {
    free(ptr);
}

extern "C" void __cxa_pure_virtual(void) {
    parsec_assert_fail();
}
