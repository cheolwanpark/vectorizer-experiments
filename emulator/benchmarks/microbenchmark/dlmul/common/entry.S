#include "config.inc"

    .section .text
    .align 2
    .globl uart_putchar
uart_putchar:
    li t0, 0x40600004
    sb a0, 0(t0)
    ret

    .align 2
    .globl uart_puts
uart_puts:
    addi sp, sp, -16
    sd ra, 8(sp)
    mv t2, a0
1:
    lbu a0, 0(t2)
    beqz a0, 2f
    call uart_putchar
    addi t2, t2, 1
    j 1b
2:
    ld ra, 8(sp)
    addi sp, sp, 16
    ret

    .align 2
    .globl uart_print_u64
uart_print_u64:
    addi sp, sp, -16
    sd ra, 8(sp)
    mv t5, a0
    bnez t5, 1f
    li a0, '0'
    call uart_putchar
    j 4f
1:
    la t0, print_buf_end
    mv t1, t0
    li t2, 10
2:
    remu t3, t5, t2
    divu t5, t5, t2
    addi t3, t3, '0'
    addi t1, t1, -1
    sb t3, 0(t1)
    bnez t5, 2b
3:
    beq t1, t0, 4f
    lbu a0, 0(t1)
    call uart_putchar
    addi t1, t1, 1
    j 3b
4:
    ld ra, 8(sp)
    addi sp, sp, 16
    ret

    .globl main
main:
    csrr s0, mcycle
    call dlmul_case_entry
    csrr s1, mcycle

    sub s2, s1, s0
    la t0, measured_cycles
    sd s2, 0(t0)

    la a0, kc_prefix
    call uart_puts
    mv a0, s2
    call uart_print_u64
    li a0, '\n'
    call uart_putchar

    li a0, 0
    .word 0x0000006b
1:
    j 1b

    .section .rodata
    .align 2
kc_prefix:
    .asciz "KC="

    .section .bss
    .align 6
    .globl input_a
input_a:
    .skip BUFFER_BYTES
    .globl input_b
input_b:
    .skip BUFFER_BYTES
    .globl input_c
input_c:
    .skip BUFFER_BYTES
    .globl input_d
input_d:
    .skip BUFFER_BYTES
    .globl input_e
input_e:
    .skip BUFFER_BYTES
    .globl input_f
input_f:
    .skip BUFFER_BYTES
    .globl input_g
input_g:
    .skip BUFFER_BYTES
    .globl input_h
input_h:
    .skip BUFFER_BYTES
    .globl output_a
output_a:
    .skip BUFFER_BYTES
    .globl output_b
output_b:
    .skip BUFFER_BYTES
    .globl measured_cycles
measured_cycles:
    .dword 0
    .align 4
print_buf:
    .skip 32
print_buf_end:
