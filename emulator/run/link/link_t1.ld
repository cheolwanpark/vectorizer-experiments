OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY {
    SCALAR (RWX) : ORIGIN = 0x20000000, LENGTH = 512M
    SRAM   (RW)  : ORIGIN = 0x60000000, LENGTH = 1024M
}

SECTIONS {
    . = ORIGIN(SCALAR);
    .text : { *(.text.init) *(.text .text.*) }
    .rodata ALIGN(0x1000) : { *(.rodata .rodata.*) }
    .data ALIGN(0x1000) : { *(.data .data.*) *(.sdata .sdata.*) }
    .bss ALIGN(0x1000) : {
        _bss_start = .;
        *(.bss .bss.*) *(.sbss .sbss.*)
        _bss_end = .;
    }
    _end = .;
    /* Provide symbols expected by t1_main.S and emurt */
    __stacktop = ORIGIN(SCALAR) + LENGTH(SCALAR);
    __heapbegin = _end;
}
