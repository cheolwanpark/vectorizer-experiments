    .section .text.init
    .globl _start
_start:
    # Disable all interrupts
    csrw mie, zero
    csrw mip, zero

    # Set trap vector to our own handler (just loops)
    la t0, _trap_handler
    csrw mtvec, t0

    # Enable FP and Vector (FS=Dirty, VS=Dirty)
    li t0, 0x00006600
    csrs mstatus, t0

    # Initialize FP and vector CSRs
    csrwi fcsr, 0       # Clear FP flags and set rounding mode to RNE
    csrwi vcsr, 0       # Clear vector CSR

    la sp, _stack_top

    la t0, _bss_start
    la t1, _bss_end
1:  beq t0, t1, 2f
    sd zero, 0(t0)
    addi t0, t0, 8
    j 1b
2:
    call main

    la t0, tohost
    li t1, 1
    sd t1, 0(t0)
3:  j 3b

    .section .tohost, "aw", @progbits
    .align 6
    .globl tohost
tohost: .dword 0
    .globl fromhost
fromhost: .dword 0

    .section .text
    .align 2
_trap_handler:
    j _trap_handler    # Just spin if trap occurs

    .section .bss
    .align 4
    .space 8192
_stack_top:
