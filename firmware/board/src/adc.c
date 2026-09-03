/* One ADC per quadrant (ADC1 IN1 PA0, ADC2 IN3 PA6, ADC3 IN12 PB0,
 * ADC4 IN4 PB14), 12 bits, continuous burst of ADC_SAMPLES into RAM
 * through DMA1 channel 1, whose DMAMUX request is switched to the
 * selected converter. Clocked from PLL P at 56.67 MHz: 2.5 cycles of
 * sampling plus 12.5 of conversion, 3.78 Msps. The four converters are
 * used one at a time (sequential quadrant scan); simultaneous capture
 * is a later firmware step. */

#include "app.h"

volatile uint16_t adc_buf[ADC_SAMPLES];

#define ADC_CLK_HZ (340000000u / 6u)
#define ADC_CYCLES_PER_SAMPLE 15u

typedef struct {
    ADC_TypeDef *adc;
    GPIO_TypeDef *port;
    uint32_t pin;
    uint32_t channel;
    uint32_t dmamux_req;   /* RM0440 DMAMUX request numbers: ADC1 5, ADC2 36, ADC3 37, ADC4 38 */
} adc_slot_t;

static const adc_slot_t slots[N_QUADRANTS] = {
    {ADC1, ADC1_PORT, ADC1_PIN, 1u, 5u},
    {ADC2, ADC2_PORT, ADC2_PIN, 3u, 36u},
    {ADC3, ADC3_PORT, ADC3_PIN, 12u, 37u},
    {ADC4, ADC4_PORT, ADC4_PIN, 4u, 38u},
};
static const adc_slot_t *cur = &slots[0];

uint32_t adc_sample_rate_hz(void) {
    return ADC_CLK_HZ / ADC_CYCLES_PER_SAMPLE;
}

static void adc_one_init(const adc_slot_t *s) {
    ADC_TypeDef *a = s->adc;
    gpio_analog(s->port, s->pin);
    a->CR &= ~ADC_CR_DEEPPWD;
    a->CR |= ADC_CR_ADVREGEN;
    delay_ns(25000u);
    a->CR &= ~ADC_CR_ADCALDIF;
    a->CR |= ADC_CR_ADCAL;
    while (a->CR & ADC_CR_ADCAL) {
    }
    delay_ns(1000u);
    a->ISR = ADC_ISR_ADRDY;
    a->CR |= ADC_CR_ADEN;
    while (!(a->ISR & ADC_ISR_ADRDY)) {
    }
    a->SQR1 = (s->channel << ADC_SQR1_SQ1_Pos);
    if (s->channel < 10u) {
        a->SMPR1 = 0u;
    } else {
        a->SMPR2 = 0u;
    }
    a->CFGR = ADC_CFGR_CONT | ADC_CFGR_DMAEN | ADC_CFGR_OVRMOD;
}

void adc_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                    RCC_AHB2ENR_ADC12EN | RCC_AHB2ENR_ADC345EN;
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN | RCC_AHB1ENR_DMAMUX1EN;
    /* both ADC clocks from PLL P */
    RCC->CCIPR = (RCC->CCIPR & ~(RCC_CCIPR_ADC12SEL | RCC_CCIPR_ADC345SEL)) |
                 (1u << RCC_CCIPR_ADC12SEL_Pos) | (1u << RCC_CCIPR_ADC345SEL_Pos);
    for (uint32_t i = 0; i < N_QUADRANTS; i++) {
        adc_one_init(&slots[i]);
    }
    adc_select(0u);
}

void adc_select(uint32_t quadrant) {
    cur = &slots[quadrant % N_QUADRANTS];
    DMAMUX1_Channel0->CCR = cur->dmamux_req;
}

void adc_capture_start(void) {
    DMA1_Channel1->CCR = 0u;
    DMA1->IFCR = DMA_IFCR_CGIF1;
    DMA1_Channel1->CPAR = (uint32_t)&cur->adc->DR;
    DMA1_Channel1->CMAR = (uint32_t)&adc_buf[0];
    DMA1_Channel1->CNDTR = ADC_SAMPLES;
    DMA1_Channel1->CCR = DMA_CCR_MINC | DMA_CCR_MSIZE_0 | DMA_CCR_PSIZE_0 |
                         DMA_CCR_EN;
    cur->adc->CR |= ADC_CR_ADSTART;
}

bool adc_capture_done(void) {
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        cur->adc->CR |= ADC_CR_ADSTP;
        while (cur->adc->CR & ADC_CR_ADSTP) {
        }
        return true;
    }
    return false;
}
