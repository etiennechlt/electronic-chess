/* Path B front: COMP1 with PA1 on its positive input, DAC3 channel 1
 * (internal) as the threshold, maximum hysteresis. The comparator
 * output feeds TIM2 channel 4 through TISEL (no external wiring) and
 * rising edges are captured into a small buffer by the TIM2 ISR.
 *
 * Bring-up note: the COMP1 INMSEL code for DAC3_CH1 and the TIM2
 * TI4SEL code for COMP1 follow RM0440; verify both on first hardware
 * bring-up with a function generator on AMP_OUT. */

#include "app.h"

#define CAPTURE_MAX 64u
static volatile uint32_t captures[CAPTURE_MAX];
static volatile uint32_t capture_n;

void comp_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_DAC3EN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    gpio_analog(GPIOA, 1u);

    /* DAC3 channel 1, internal output only, threshold at the VREF bias. */
    DAC3->MCR = (DAC3->MCR & ~DAC_MCR_MODE1) | (3u << DAC_MCR_MODE1_Pos);
    DAC3->CR |= DAC_CR_EN1;
    delay_ns(10000u);
    DAC3->DHR12R1 = (uint32_t)((VREF_BIAS_V / 3.3f) * 4095.0f);

    /* COMP1: INP = PA1, INM = DAC3_CH1, large hysteresis. */
    COMP1->CSR = (4u << COMP_CSR_INMSEL_Pos) |   /* DAC3_CH1 per RM0440 */
                 (0u << COMP_CSR_INPSEL_Pos) |   /* PA1 */
                 (5u << COMP_CSR_HYST_Pos) |
                 COMP_CSR_EN;

    /* TIM2 free-running at sysclk, CH4 input capture from COMP1. */
    TIM2->PSC = 0u;
    TIM2->ARR = 0xFFFFFFFFu;
    TIM2->TISEL = (1u << TIM_TISEL_TI4SEL_Pos);  /* TI4 = COMP1 output */
    TIM2->CCMR2 |= (1u << TIM_CCMR2_CC4S_Pos);   /* CC4 <- TI4 */
    TIM2->CCER &= ~(TIM_CCER_CC4P | TIM_CCER_CC4NP);  /* rising edges */
    TIM2->CR1 |= TIM_CR1_CEN;
    NVIC_EnableIRQ(TIM2_IRQn);
}

void comp_capture_arm(void) {
    capture_n = 0u;
    TIM2->SR = 0u;
    TIM2->CCER |= TIM_CCER_CC4E;
    TIM2->DIER |= TIM_DIER_CC4IE;
}

void TIM2_IRQHandler(void) {
    if (TIM2->SR & TIM_SR_CC4IF) {
        uint32_t v = TIM2->CCR4;  /* reading clears CC4IF */
        if (capture_n < CAPTURE_MAX) {
            captures[capture_n++] = v;
        } else {
            TIM2->DIER &= ~TIM_DIER_CC4IE;
            TIM2->CCER &= ~TIM_CCER_CC4E;
        }
    }
}

uint32_t comp_capture_count(void) {
    return capture_n;
}

uint32_t comp_capture_get(uint32_t idx) {
    return captures[idx];
}
