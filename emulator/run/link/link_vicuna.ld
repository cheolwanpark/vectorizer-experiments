/* Vicuna Vector Coprocessor Linker Script
 * Based on vicuna/sw/lld_link.ld
 * Memory map:
 *   Boot: 0x00000000 - 0x00002000 (8 KB)
 *   RAM:  0x00002000 - 0x00040000 (248 KB)
 */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    boot : ORIGIN = 0x00000000, LENGTH = 0x00002000 /*   8 kB */
    ram  : ORIGIN = 0x00002000, LENGTH = 0x0003E000 /* 248 kB */
}

STACK_LEN = 0x4000; /* 16 kB */

SECTIONS
{
    /* Interrupt vectors at address 0 */
    .vectors 0 : {
        *(.vectors)
    } > boot

    /* Code section */
    .text : {
        . = ALIGN(4);
        _stext = .;
        *(.text.init)
        *(.text)
        *(.text.*)
        _etext = .;
        . = ALIGN(4);
    } > ram

    /* Read-only data */
    .rodata : {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata.*)
        *(.srodata)
        *(.srodata.*)
        . = ALIGN(4);
    } > ram

    /* Initialized data */
    .data : {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data.*)
        *(.sdata)
        *(.sdata.*)
        _edata = .;
        . = ALIGN(4);
    } > ram

    /* Uninitialized data */
    .bss (NOLOAD) : {
        . = ALIGN(4);
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(.sbss)
        *(.sbss.*)
        *(COMMON)
        _bss_end = .;
        . = ALIGN(4);
    } > ram

    _end = .;

    /* Stack at end of RAM */
    .stack ORIGIN(ram) + LENGTH(ram) - STACK_LEN (NOLOAD) : {
        . = ALIGN(16);
        _stack_start = .;
        . = . + STACK_LEN;
        . = ALIGN(16);
        _stack = .;
    } > ram

    /* Discard debug sections */
    /DISCARD/ : {
        *(.eh_frame)
        *(.comment)
        *(.note.*)
    }
}
