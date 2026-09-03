/* CMSIS SystemInit and SystemCoreClock for the bare-metal build. */

#include "stm32g474xx.h"

uint32_t SystemCoreClock = 16000000u;

void SystemInit(void) {
    /* Enable FPU access (CP10/CP11 full access). */
    SCB->CPACR |= (3u << 20) | (3u << 22);
}
