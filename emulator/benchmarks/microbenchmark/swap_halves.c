#include <stdint.h>
#include <stddef.h>
#include <riscv_vector.h>
#ifdef USE_HOST_SYSCALL
#include <stdio.h>
#endif

#ifndef USE_HOST_SYSCALL
#ifndef USE_UARTLITE
#define USE_UARTLITE 0
#endif

#if USE_UARTLITE
#define UARTLITE_MMIO 0x40600000UL
#define UARTLITE_TX_FIFO 0x4
#define UARTLITE_STAT_REG 0x8
#define UARTLITE_CTRL_REG 0xc
#define UARTLITE_RST_FIFO 0x03
#define UARTLITE_TX_FULL 0x08

static inline void mmio_write8(uintptr_t addr, uint8_t value) {
  *(volatile uint8_t *)addr = value;
}

static inline uint8_t mmio_read8(uintptr_t addr) {
  return *(volatile uint8_t *)addr;
}

static inline void uartlite_init(void) {
  mmio_write8(UARTLITE_MMIO + UARTLITE_CTRL_REG, UARTLITE_RST_FIFO);
}

static inline void uartlite_putc(char c) {
  if (c == '\n') uartlite_putc('\r');
  while (mmio_read8(UARTLITE_MMIO + UARTLITE_STAT_REG) & UARTLITE_TX_FULL)
    ;
  mmio_write8(UARTLITE_MMIO + UARTLITE_TX_FIFO, (uint8_t)c);
}

static void uartlite_print_str(const char *s) {
  while (*s) uartlite_putc(*s++);
}

static void uartlite_print_u64(uint64_t v) {
  char buf[32];
  int i = 0;
  if (v == 0) {
    uartlite_putc('0');
    return;
  }
  while (v && i < (int)sizeof(buf)) {
    buf[i++] = '0' + (v % 10);
    v /= 10;
  }
  while (--i >= 0) uartlite_putc(buf[i]);
}

static void uartlite_print_hex32(uint32_t v) {
  for (int i = 7; i >= 0; --i) {
    uint32_t nib = (v >> (i * 4)) & 0xF;
    uartlite_putc(nib < 10 ? '0' + nib : 'a' + (nib - 10));
  }
}

static inline void uartlite_exit(void) {
  __asm__ volatile("ebreak");
  while (1)
    ;
}

#define WRITE_STR uartlite_print_str
#define WRITE_U64 uartlite_print_u64
#define WRITE_HEX32 uartlite_print_hex32
#define EXIT_OK()            \
  do {                       \
    uartlite_exit();         \
    __builtin_unreachable(); \
  } while (0)
#else
#ifndef EXTERN_TOTOHOST
volatile uint64_t tohost __attribute__((section(".tohost"), aligned(64)));
volatile uint64_t fromhost __attribute__((section(".tohost"), aligned(64)));
#else
extern volatile uint64_t tohost;
extern volatile uint64_t fromhost;
#endif

#define HTIF_DEV_SHIFT 56
#define HTIF_CMD_SHIFT 48
#define HTIF_DEV_MASK 0xff
#define HTIF_CMD_MASK 0xff
#define HTIF_PAYLOAD_MASK ((1ULL << HTIF_CMD_SHIFT) - 1)

static inline uint64_t htif_pack(uint64_t dev, uint64_t cmd, uint64_t payload) {
  return ((dev & HTIF_DEV_MASK) << HTIF_DEV_SHIFT) |
         ((cmd & HTIF_CMD_MASK) << HTIF_CMD_SHIFT) |
         (payload & HTIF_PAYLOAD_MASK);
}

static inline void htif_send(uint64_t dev, uint64_t cmd, uint64_t payload) {
  while (tohost != 0)
    ;
  tohost = htif_pack(dev, cmd, payload);
  while (tohost != 0)
    ;
}

static inline void htif_putc(char c) { htif_send(1, 1, (uint8_t)c); }

static void htif_print_str(const char *s) {
  while (*s) htif_putc(*s++);
}

static void htif_print_u64(uint64_t v) {
  char buf[32];
  int i = 0;
  if (v == 0) {
    htif_putc('0');
    return;
  }
  while (v && i < (int)sizeof(buf)) {
    buf[i++] = '0' + (v % 10);
    v /= 10;
  }
  while (--i >= 0) htif_putc(buf[i]);
}

static void htif_print_hex32(uint32_t v) {
  for (int i = 7; i >= 0; --i) {
    uint32_t nib = (v >> (i * 4)) & 0xF;
    htif_putc(nib < 10 ? '0' + nib : 'a' + (nib - 10));
  }
}

static inline void htif_exit(uint64_t code) {
  htif_send(0, 0, (code << 1) | 1);
  while (1)
    ;
}

#define WRITE_STR htif_print_str
#define WRITE_U64 htif_print_u64
#define WRITE_HEX32 htif_print_hex32
#define EXIT_OK()            \
  do {                       \
    htif_exit(0);            \
    __builtin_unreachable(); \
  } while (0)
#endif
#else
#define WRITE_STR(s) fputs((s), stdout)
#define WRITE_U64(v) fprintf(stdout, "%llu", (unsigned long long)(v))
#define WRITE_HEX32(v) fprintf(stdout, "%08x", (uint32_t)(v))
#define EXIT_OK() return 0
#endif

#ifndef DATA_LEN
#define DATA_LEN 64
#endif

#ifndef WARMUP_ITERS
#define WARMUP_ITERS 10
#endif

#ifndef MEASURE_ITERS
#define MEASURE_ITERS 1000
#endif

volatile uint64_t results[4] __attribute__((aligned(16)));

static inline uint64_t rdcycle(void) {
  uint64_t cycles;
  __asm__ volatile("fence" ::: "memory");
  __asm__ volatile("rdcycle %0" : "=r"(cycles));
  __asm__ volatile("fence" ::: "memory");
  return cycles;
}

static inline uint32_t f2u(float f) {
  union {
    float f;
    uint32_t u;
  } v = { .f = f };
  return v.u;
}

static uint64_t checksum_bits(const float *buf, size_t n) {
  uint64_t acc = 0;
  for (size_t i = 0; i < n; ++i) {
    acc += f2u(buf[i]);
  }
  return acc;
}

__attribute__((noinline)) static void bench_gather(size_t n, float *a, float *b, uint32_t *idx) {
  size_t vl = __riscv_vsetvl_e32m1(n);
  vfloat32m1_t va = __riscv_vle32_v_f32m1(a, vl);
  vuint32m1_t vi = __riscv_vle32_v_u32m1(idx, vl);
  vfloat32m1_t res = __riscv_vrgather_vv_f32m1(va, vi, vl);
  __riscv_vse32_v_f32m1(b, res, vl);
}

__attribute__((noinline)) static void bench_slide(size_t n, float *a, float *b) {
  size_t vl = __riscv_vsetvl_e32m1(n);
  size_t half = vl / 2;
  vfloat32m1_t va = __riscv_vle32_v_f32m1(a, vl);
  vfloat32m1_t lo = __riscv_vslidedown_vx_f32m1(va, half, vl);
  vfloat32m1_t res = __riscv_vslideup_vx_f32m1(lo, va, half, vl);
  __riscv_vse32_v_f32m1(b, res, vl);
}

int main(void) {
  static float src[DATA_LEN] __attribute__((aligned(64)));
  static float dst[DATA_LEN] __attribute__((aligned(64)));
  static uint32_t idx[DATA_LEN] __attribute__((aligned(64)));

  size_t n = __riscv_vsetvl_e32m1(DATA_LEN);
  n &= ~1ULL;
  if (n < 2) n = 2;

  for (size_t i = 0; i < n; ++i) {
    src[i] = (float)i;
    idx[i] = (i < n / 2) ? (uint32_t)(i + n / 2) : (uint32_t)(i - n / 2);
  }

#if USE_UARTLITE
  uartlite_init();
#endif

  for (int i = 0; i < WARMUP_ITERS; ++i) {
    bench_gather(n, src, dst, idx);
  }

  uint64_t start_g = rdcycle();
  for (int i = 0; i < MEASURE_ITERS; ++i) {
    bench_gather(n, src, dst, idx);
  }
  uint64_t end_g = rdcycle();
  uint64_t chk_g = checksum_bits(dst, n);

  for (int i = 0; i < WARMUP_ITERS; ++i) {
    bench_slide(n, src, dst);
  }

  uint64_t start_s = rdcycle();
  for (int i = 0; i < MEASURE_ITERS; ++i) {
    bench_slide(n, src, dst);
  }
  uint64_t end_s = rdcycle();
  uint64_t chk_s = checksum_bits(dst, n);

  uint64_t avg_g = (end_g - start_g) / MEASURE_ITERS;
  uint64_t avg_s = (end_s - start_s) / MEASURE_ITERS;

  results[0] = avg_g;
  results[1] = avg_s;
  results[2] = chk_g;
  results[3] = chk_s;

  WRITE_STR("RES gather_avg=");
  WRITE_U64(avg_g);
  WRITE_STR(" slide_avg=");
  WRITE_U64(avg_s);
  WRITE_STR(" chk_g=0x");
  WRITE_HEX32((uint32_t)chk_g);
  WRITE_STR(" chk_s=0x");
  WRITE_HEX32((uint32_t)chk_s);
  WRITE_STR("\n");
  EXIT_OK();
}
