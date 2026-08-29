/* Board-level constants and helpers for the 2x2 mockup on NUCLEO-G474RE. */

#ifndef BOARD_H
#define BOARD_H

#include <stdint.h>

#include "stm32g474xx.h"

#include "board_pins.h"

#define SYSCLK_HZ 170000000u

/* Analog chain constants (mirrors config/board.yaml). */
#define VREF_BIAS_V 1.65f
#define N_SQUARES 4u
#define ADC_SAMPLES 512u
#define BAND_LO_HZ 200000u
#define BAND_HI_HZ 650000u
#define DRIVE_PULSE_NS 1000u
#define BLANKING_NS 2000u

static inline void gpio_set(GPIO_TypeDef *port, uint32_t pin) {
    port->BSRR = 1u << pin;
}

static inline void gpio_clear(GPIO_TypeDef *port, uint32_t pin) {
    port->BSRR = 1u << (pin + 16u);
}

static inline void gpio_out(GPIO_TypeDef *port, uint32_t pin) {
    port->MODER = (port->MODER & ~(3u << (2u * pin))) | (1u << (2u * pin));
}

static inline void gpio_analog(GPIO_TypeDef *port, uint32_t pin) {
    port->MODER |= 3u << (2u * pin);
}

static inline void gpio_af(GPIO_TypeDef *port, uint32_t pin, uint32_t af) {
    port->MODER = (port->MODER & ~(3u << (2u * pin))) | (2u << (2u * pin));
    volatile uint32_t *afr = &port->AFR[pin >> 3u];
    uint32_t shift = 4u * (pin & 7u);
    *afr = (*afr & ~(0xFu << shift)) | (af << shift);
}

/* Cycle-accurate busy wait via DWT. */
void dwt_init(void);
void delay_ns(uint32_t ns);
void delay_ms(uint32_t ms);

#endif
