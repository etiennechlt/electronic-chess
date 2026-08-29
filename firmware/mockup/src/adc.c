/* ADC1 channel 1 (PA0), 12 bits, continuous burst of ADC_SAMPLES into
 * RAM through DMA1 channel 1. Clocked from PLL P at 56.67 MHz: with
 * 2.5 cycles of sampling plus 12.5 of conversion, one sample every
 * 15 cycles, i.e. 3.78 Msps (the 4 Msps of the brief is the ADC's
 * ceiling; the FFT bin math uses the real rate). */

#include "app.h"

volatile uint16_t adc_buf[ADC_SAMPLES];

#define ADC_CLK_HZ (340000000u / 6u)
#define ADC_CYCLES_PER_SAMPLE 15u

uint32_t adc_sample_rate_hz(void) {
    return ADC_CLK_HZ / ADC_CYCLES_PER_SAMPLE;
}

void adc_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_ADC12EN;
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN | RCC_AHB1ENR_DMAMUX1EN;
    gpio_analog(GPIOA, 0u);

    /* ADC12 clock: PLL P. */
    RCC->CCIPR = (RCC->CCIPR & ~RCC_CCIPR_ADC12SEL) |
                 (1u << RCC_CCIPR_ADC12SEL_Pos);

    /* Exit deep power down, start the regulator, calibrate. */
    ADC1->CR &= ~ADC_CR_DEEPPWD;
    ADC1->CR |= ADC_CR_ADVREGEN;
    delay_ns(25000u);
    ADC1->CR &= ~ADC_CR_ADCALDIF;
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) {
    }
    delay_ns(1000u);

    ADC1->ISR = ADC_ISR_ADRDY;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) {
    }

    /* Channel 1, minimum sampling time, continuous conversion. */
    ADC1->SQR1 = (1u << ADC_SQR1_SQ1_Pos); /* one conversion: channel 1 */
    ADC1->SMPR1 = 0u;                       /* 2.5 cycles for channel 1 */
    ADC1->CFGR = ADC_CFGR_CONT | ADC_CFGR_DMAEN | ADC_CFGR_OVRMOD;

    /* DMA1 channel 1 through DMAMUX request 5 (ADC1). */
    DMAMUX1_Channel0->CCR = 5u;
}

void adc_capture_start(void) {
    DMA1_Channel1->CCR = 0u;
    DMA1->IFCR = DMA_IFCR_CGIF1;
    DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR = (uint32_t)&adc_buf[0];
    DMA1_Channel1->CNDTR = ADC_SAMPLES;
    DMA1_Channel1->CCR = DMA_CCR_MINC | DMA_CCR_MSIZE_0 | DMA_CCR_PSIZE_0 |
                         DMA_CCR_EN;
    ADC1->CR |= ADC_CR_ADSTART;
}

bool adc_capture_done(void) {
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        ADC1->CR |= ADC_CR_ADSTP;
        while (ADC1->CR & ADC_CR_ADSTP) {
        }
        return true;
    }
    return false;
}
