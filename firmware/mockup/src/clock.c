/* 170 MHz from HSI16 through the PLL, boost mode, flash 4 WS. */

#include "app.h"

extern uint32_t SystemCoreClock;

void clock_init_170mhz(void) {
    /* Boost regulator range for 170 MHz. */
    RCC->APB1ENR1 |= RCC_APB1ENR1_PWREN;
    PWR->CR5 &= ~PWR_CR5_R1MODE;

    FLASH->ACR = (FLASH->ACR & ~FLASH_ACR_LATENCY) | FLASH_ACR_LATENCY_4WS |
                 FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN;

    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {
    }

    /* PLL: HSI16 / M(4) * N(85) = 340 MHz VCO, R/2 -> 170 MHz sysclk,
     * P divider -> 56.67 MHz for the ADC (340 / 6). */
    RCC->CR &= ~RCC_CR_PLLON;
    while (RCC->CR & RCC_CR_PLLRDY) {
    }
    RCC->PLLCFGR =
        RCC_PLLCFGR_PLLSRC_HSI |
        ((4u - 1u) << RCC_PLLCFGR_PLLM_Pos) |
        (85u << RCC_PLLCFGR_PLLN_Pos) |
        (0u << RCC_PLLCFGR_PLLR_Pos) |      /* R = 2 */
        RCC_PLLCFGR_PLLREN |
        (6u << RCC_PLLCFGR_PLLPDIV_Pos) |   /* P = VCO / 6 */
        RCC_PLLCFGR_PLLPEN;
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {
    }

    /* AHB at 170 immediately is allowed once boost is set and latency
     * programmed; APB1/APB2 at /1. */
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {
    }
    SystemCoreClock = SYSCLK_HZ;
}

void dwt_init(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0u;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

void delay_ns(uint32_t ns) {
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = (uint32_t)(((uint64_t)ns * SYSCLK_HZ) / 1000000000u);
    while ((DWT->CYCCNT - start) < cycles) {
    }
}

void delay_ms(uint32_t ms) {
    while (ms--) {
        delay_ns(1000000u);
    }
}
