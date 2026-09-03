/* Path B front on quadrant 1 only: COMP3 with PA0 (shared with ADC1) on
 * its positive input, DAC3 channel 1 (internal) as the threshold,
 * maximum hysteresis, output captured by TIM2 channel 4 through TISEL.
 *
 * Bring-up note: the COMP3 INMSEL code for DAC3_CH1 and the TIM2
 * TI4SEL code for COMP3 are taken from RM0440 tables from memory and
 * must be checked on first hardware bring-up with a function generator
 * on AMP_OUT1; the mockup firmware validated the same scheme on COMP1. */

#include "app.h"

#define CAPTURE_MAX 64u
#define COMP3_INMSEL_DAC3_CH1 4u   /* verify against RM0440 */
#define TIM2_TI4SEL_COMP3 3u       /* verify against RM0440 */

static volatile uint32_t captures[CAPTURE_MAX];
static volatile uint32_t capture_n;

void comp_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_DAC3EN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    gpio_analog(ADC1_PORT, ADC1_PIN);

    DAC3->MCR = (DAC3->MCR & ~DAC_MCR_MODE1) | (3u << DAC_MCR_MODE1_Pos);
    DAC3->CR |= DAC_CR_EN1;
    delay_ns(10000u);
    DAC3->DHR12R1 = (uint32_t)((VREF_BIAS_V / 3.3f) * 4095.0f);

    COMP3->CSR = (COMP3_INMSEL_DAC3_CH1 << COMP_CSR_INMSEL_Pos) |
                 (0u << COMP_CSR_INPSEL_Pos) |   /* PA0 */
                 (5u << COMP_CSR_HYST_Pos) |
                 COMP_CSR_EN;

    TIM2->PSC = 0u;
    TIM2->ARR = 0xFFFFFFFFu;
    TIM2->TISEL = (TIM2_TI4SEL_COMP3 << TIM_TISEL_TI4SEL_Pos);
    TIM2->CCMR2 |= (1u << TIM_CCMR2_CC4S_Pos);
    TIM2->CCER &= ~(TIM_CCER_CC4P | TIM_CCER_CC4NP);
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
        uint32_t v = TIM2->CCR4;
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
