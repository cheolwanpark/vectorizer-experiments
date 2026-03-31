# Vicuna Vector Coprocessor CRT
# Based on vicuna/sw/crt0.S but simplified for benchmark use
# Termination: jump to address 0 triggers simulation end

    .section .vectors, "ax", @progbits
    .option norvc;

    # Interrupt vectors (redirect to infinite loop)
    .rept 31
    nop
    .endr
    j exc_handler

    # Reset vector - redirect to _start
    j _start


    .section .text
    .global _start
    .type   _start, @function
_start:
    # Enable vector extension in mstatus (VS = Dirty = 0x600)
    li t0, 0x00000600
    csrs mstatus, t0

    # Initialize vector CSR
    csrwi vcsr, 0

    # Initialize stack pointer
    la sp, _stack

    # Clear BSS section
    la t1, _bss_start
    la t2, _bss_end
    bge t1, t2, bss_clear_end

bss_clear_loop:
    sw x0, 0(t1)
    addi t1, t1, 4
    blt t1, t2, bss_clear_loop

bss_clear_end:
    # Call main (argc = 0, argv = 0)
    li a0, 0
    li a1, 0
    call main

    # Termination: jump to address 0
    # This triggers Vicuna simulator to end
    jr x0


# Default exception handler (infinite loop)
    .weak exc_handler
    .type exc_handler, @function
exc_handler:
    j exc_handler
