/* Board-level constants and helpers for the brain board (STM32G474RE),
 * driving four 4x4 quadrants (ADR 0010). */

#ifndef BOARD_H
#define BOARD_H

#include <stdint.h>

#include "stm32g474xx.h"

#include "board_pins.h"

#define SYSCLK_HZ 170000000u

/* Analog chain constants (mirrors config/board.yaml). */
#define VREF_BIAS_V 1.65f
#define N_QUADRANTS 4u
#define COILS_PER_QUADRANT 16u
#define N_SQUARES (N_QUADRANTS * COILS_PER_QUADRANT)
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

static inline void gpio_write(GPIO_TypeDef *port, uint32_t pin, uint32_t level) {
    if (level) {
        gpio_set(port, pin);
    } else {
        gpio_clear(port, pin);
    }
}

static inline uint32_t gpio_read(GPIO_TypeDef *port, uint32_t pin) {
    return (port->IDR >> pin) & 1u;
}

static inline void gpio_out(GPIO_TypeDef *port, uint32_t pin) {
    port->MODER = (port->MODER & ~(3u << (2u * pin))) | (1u << (2u * pin));
}

static inline void gpio_in_pullup(GPIO_TypeDef *port, uint32_t pin) {
    port->MODER &= ~(3u << (2u * pin));
    port->PUPDR = (port->PUPDR & ~(3u << (2u * pin))) | (1u << (2u * pin));
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
