OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS {
    . = 0x80000000;
    .text.init : { *(.text.init) }
    .tohost ALIGN(0x1000) : { *(.tohost) }
    .text ALIGN(0x1000) : { *(.text .text.*) }
    .rodata ALIGN(0x1000) : { *(.rodata .rodata.*) }
    .data ALIGN(0x1000) : { *(.data .data.*) *(.sdata .sdata.*) }
    .bss ALIGN(0x1000) : {
        _bss_start = .;
        *(.bss .bss.*) *(.sbss .sbss.*)
        _bss_end = .;
    }
    _end = .;
}
