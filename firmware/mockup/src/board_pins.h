/* Generated from config/board.yaml by scripts/gen_pins.py. Do not edit. */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

#define AMP_OUT_PORT GPIOA
#define AMP_OUT_PIN 0u
/* AMP_OUT: PA0, Arduino A0 */

#define COMP_IN_PORT GPIOA
#define COMP_IN_PIN 1u
/* COMP_IN: PA1, Arduino A1 */

#define PULSE_EN_PORT GPIOA
#define PULSE_EN_PIN 4u
/* PULSE_EN: PA4, Arduino A2 */

#define MUX_A0_PORT GPIOB
#define MUX_A0_PIN 3u
/* MUX_A0: PB3, Arduino D3 */

#define MUX_A1_PORT GPIOB
#define MUX_A1_PIN 5u
/* MUX_A1: PB5, Arduino D4 */

#define MUX_INH_PORT GPIOB
#define MUX_INH_PIN 4u
/* MUX_INH: PB4, Arduino D5 */

#define DAMP_1_PORT GPIOB
#define DAMP_1_PIN 10u
/* DAMP_1: PB10, Arduino D6 */

#define DAMP_2_PORT GPIOA
#define DAMP_2_PIN 8u
/* DAMP_2: PA8, Arduino D7 */

#define DAMP_3_PORT GPIOC
#define DAMP_3_PIN 7u
/* DAMP_3: PC7, Arduino D9 */

#define DAMP_4_PORT GPIOB
#define DAMP_4_PIN 6u
/* DAMP_4: PB6, Arduino D10 */

#define DRIVE_1_PORT GPIOA
#define DRIVE_1_PIN 7u
/* DRIVE_1: PA7, Arduino D11 */

#define DRIVE_2_PORT GPIOA
#define DRIVE_2_PIN 6u
/* DRIVE_2: PA6, Arduino D12 */

#define DRIVE_3_PORT GPIOB
#define DRIVE_3_PIN 9u
/* DRIVE_3: PB9, Arduino D14 */

#define DRIVE_4_PORT GPIOB
#define DRIVE_4_PIN 8u
/* DRIVE_4: PB8, Arduino D15 */

#define LED_DIN_PORT GPIOA
#define LED_DIN_PIN 5u
/* LED_DIN: PA5, Arduino D13 */

#define PI_UART_TX_PORT GPIOA
#define PI_UART_TX_PIN 9u
/* PI_UART_TX: PA9, Arduino D8 */

#define PI_UART_RX_PORT GPIOA
#define PI_UART_RX_PIN 10u
/* PI_UART_RX: PA10, Arduino D2 */

#define LED_COUNT 8u
/* zero-based square index per chain position */
#define LED_CHAIN_SQ { 1u, 1u, 3u, 3u, 2u, 2u, 0u, 0u }
#define LED_COLOR_WHITE 0xFFAA3Cu
#define LED_COLOR_BLACK 0x283CFFu

#endif
