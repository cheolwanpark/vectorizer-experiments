OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .text : { *(.text) }
  . = ALIGN(0x1000);
  .rodata : { *(.rodata*) }
  .data : { *(.data) }
  .bss : {
    _bss_start = .;
    *(.bss*) *(COMMON)
    _bss_end = .;
  }

  . = ALIGN(64);
  _stack_top = . + 0x10000; /* 64 KiB stack */
}
