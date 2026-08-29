/* Minimal C startup for STM32G474: vector table, data/bss init. */

#include <stdint.h>

extern uint32_t _etext, _sdata, _edata, _sbss, _ebss, _estack;

int main(void);
void SystemInit(void);

void Reset_Handler(void) {
    const uint32_t *src = &_etext;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }
    for (dst = &_sbss; dst < &_ebss; dst++) {
        *dst = 0u;
    }
    SystemInit();
    main();
    for (;;) {
    }
}

void Default_Handler(void) {
    for (;;) {
    }
}

#define WEAK_ALIAS __attribute__((weak, alias("Default_Handler")))
void NMI_Handler(void) WEAK_ALIAS;
void HardFault_Handler(void) WEAK_ALIAS;
void MemManage_Handler(void) WEAK_ALIAS;
void BusFault_Handler(void) WEAK_ALIAS;
void UsageFault_Handler(void) WEAK_ALIAS;
void SVC_Handler(void) WEAK_ALIAS;
void DebugMon_Handler(void) WEAK_ALIAS;
void PendSV_Handler(void) WEAK_ALIAS;
void SysTick_Handler(void) WEAK_ALIAS;
void DMA1_Channel1_IRQHandler(void) WEAK_ALIAS;
void USART2_IRQHandler(void) WEAK_ALIAS;
void TIM2_IRQHandler(void) WEAK_ALIAS;

/* Only the exceptions and the few peripheral vectors this firmware
 * uses are populated by name; the rest default. The table is padded to
 * the highest IRQ number of the G474 (101). */
__attribute__((section(".isr_vector"), used))
static void (*const vector_table[16 + 102])(void) = {
    (void (*)(void))((uintptr_t)&_estack),
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    MemManage_Handler,
    BusFault_Handler,
    UsageFault_Handler,
    0, 0, 0, 0,
    SVC_Handler,
    DebugMon_Handler,
    0,
    PendSV_Handler,
    SysTick_Handler,
    /* IRQ 0.. */
    [16 + 11] = DMA1_Channel1_IRQHandler,
    [16 + 28] = TIM2_IRQHandler,
    [16 + 38] = USART2_IRQHandler,
};
