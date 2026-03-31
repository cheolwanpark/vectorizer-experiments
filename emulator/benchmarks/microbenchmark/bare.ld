ENTRY(_start)

SECTIONS
{
  . = 0x80000000;
  .text : {
    *(.text.init)
    *(.text*)
  }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  .bss : {
    _bss_start = .;
    *(.bss*) *(COMMON)
    _bss_end = .;
  }
  . = ALIGN(64);
  .tohost : { *(.tohost) }

  . = ALIGN(16);
  _stack_top = . + 0x10000; /* 64 KiB stack */
}
