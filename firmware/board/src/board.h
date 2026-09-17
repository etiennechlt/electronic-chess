/* Board-level constants and helpers for the brain board (STM32G474RE),
 * driving four 4x4 quadrants (ADR 0010). Built with NUCLEO=1 the same
 * firmware runs on a Nucleo-G474RE driving one reduced 2x2 quadrant
 * over the brain's bus pins: the bench of note 19. */

#ifndef BOARD_H
#define BOARD_H

#include <stdint.h>

#include "stm32g474xx.h"

#include "board_pins.h"

#ifndef NUCLEO
#define NUCLEO 0
#endif

#define SYSCLK_HZ 170000000u

/* Analog chain constants (mirrors config/board.yaml). */
#define VREF_BIAS_V 1.65f
#define ADC_SAMPLES 512u
#define BAND_LO_HZ 200000u
#define BAND_HI_HZ 650000u
#define DRIVE_PULSE_NS 1000u
#define BLANKING_NS 2000u

/* Grid, LED chain and console of the two targets (values from board_pins.h). */
#if NUCLEO
#define BOARD_NAME "nucleo bench"
#define N_QUADRANTS 1u
#define COILS_PER_ROW REDUCED_SQUARES
#define LED_N NUCLEO_LED_COUNT
#define LED_CHAIN NUCLEO_LED_CHAIN_SQ
#define CONSOLE_TX_PORT NUCLEO_CONSOLE_TX_PORT
#define CONSOLE_TX_PIN NUCLEO_CONSOLE_TX_PIN
#define CONSOLE_RX_PORT NUCLEO_CONSOLE_RX_PORT
#define CONSOLE_RX_PIN NUCLEO_CONSOLE_RX_PIN
#if NUCLEO_CONSOLE_USART == 2u
#define CONSOLE_USART USART2
#define CONSOLE_CLK_ENABLE() (RCC->APB1ENR1 |= RCC_APB1ENR1_USART2EN)
#else
#error "bench.console.usart in config/board.yaml: only USART2 is wired here"
#endif
#else
#define BOARD_NAME "brain"
#define N_QUADRANTS PLATEAU_QUADRANTS
#define COILS_PER_ROW QUADRANT_SQUARES
#define LED_N LED_COUNT
#define LED_CHAIN LED_CHAIN_SQ
#define CONSOLE_TX_PORT MCU_TX_PORT
#define CONSOLE_TX_PIN MCU_TX_PIN
#define CONSOLE_RX_PORT MCU_RX_PORT
#define CONSOLE_RX_PIN MCU_RX_PIN
#define CONSOLE_USART USART1
#define CONSOLE_CLK_ENABLE() (RCC->APB2ENR |= RCC_APB2ENR_USART1EN)
#endif
#define COILS_PER_QUADRANT (COILS_PER_ROW * COILS_PER_ROW)
#define N_SQUARES (N_QUADRANTS * COILS_PER_QUADRANT)

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

/* Clock of the port a generated pin lives on (ports A to D on the LQFP64). */
static inline void gpio_clock_enable(GPIO_TypeDef *port) {
    if (port == GPIOA) {
        RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    } else if (port == GPIOB) {
        RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    } else if (port == GPIOC) {
        RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    } else if (port == GPIOD) {
        RCC->AHB2ENR |= RCC_AHB2ENR_GPIODEN;
    }
}

/* Cycle-accurate busy wait via DWT. */
void dwt_init(void);
void delay_ns(uint32_t ns);
void delay_ms(uint32_t ms);

#endif
