/* STM32G474RE: 512K flash, 96K SRAM (SRAM1+SRAM2 contiguous), 32K CCM.
 * The last 2K flash page (0x0807F800) is reserved for calibration data. */
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 510K
  CALIB (r)   : ORIGIN = 0x0807F800, LENGTH = 2K
  RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 96K
  CCMRAM (rwx): ORIGIN = 0x10000000, LENGTH = 32K
}

ENTRY(Reset_Handler)

_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH

  .text : {
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
  } > FLASH

  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > FLASH
  .ARM.exidx : {
    __exidx_start = .;
    *(.ARM.exidx*)
    __exidx_end = .;
  } > FLASH

  .data : {
    . = ALIGN(4);
    _sdata = .;
    *(.data*)
    . = ALIGN(4);
    _edata = .;
  } > RAM AT > FLASH
  _etext = LOADADDR(.data);

  .bss : {
    . = ALIGN(4);
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM

}
