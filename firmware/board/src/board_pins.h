/* Generated from config/board.yaml by scripts/gen_pins.py. Do not edit. */
#ifndef BOARD_PINS_H
#define BOARD_PINS_H

#define ADC1_PORT GPIOA
#define ADC1_PIN 0u
/* ADC1: PA0 */

#define ADC2_PORT GPIOA
#define ADC2_PIN 6u
/* ADC2: PA6 */

#define ADC3_PORT GPIOB
#define ADC3_PIN 0u
/* ADC3: PB0 */

#define ADC4_PORT GPIOB
#define ADC4_PIN 14u
/* ADC4: PB14 */

#define LED_DIN_MCU_PORT GPIOA
#define LED_DIN_MCU_PIN 5u
/* LED_DIN_MCU: PA5 */

#define MUX_A0_PORT GPIOB
#define MUX_A0_PIN 3u
/* MUX_A0: PB3 */

#define MUX_A1_PORT GPIOB
#define MUX_A1_PIN 5u
/* MUX_A1: PB5 */

#define MUX_A2_PORT GPIOB
#define MUX_A2_PIN 4u
/* MUX_A2: PB4 */

#define MUX_EN_L_PORT GPIOC
#define MUX_EN_L_PIN 0u
/* MUX_EN_L: PC0 */

#define MUX_EN_H_PORT GPIOC
#define MUX_EN_H_PIN 1u
/* MUX_EN_H: PC1 */

#define PULSE_EN_PORT GPIOA
#define PULSE_EN_PIN 4u
/* PULSE_EN: PA4 */

#define DAMP_EN_N_PORT GPIOC
#define DAMP_EN_N_PIN 2u
/* DAMP_EN_N: PC2 */

#define STEP1_PORT GPIOC
#define STEP1_PIN 6u
/* STEP1: PC6 */

#define DIR1_PORT GPIOC
#define DIR1_PIN 7u
/* DIR1: PC7 */

#define STEP2_PORT GPIOC
#define STEP2_PIN 8u
/* STEP2: PC8 */

#define DIR2_PORT GPIOC
#define DIR2_PIN 9u
/* DIR2: PC9 */

#define MOT_EN_PORT GPIOC
#define MOT_EN_PIN 12u
/* MOT_EN: PC12 */

#define TMC_TX_PORT GPIOC
#define TMC_TX_PIN 10u
/* TMC_TX: PC10 */

#define TMC_RX_PORT GPIOC
#define TMC_RX_PIN 11u
/* TMC_RX: PC11 */

#define ENDSTOP_X_PORT GPIOD
#define ENDSTOP_X_PIN 2u
/* ENDSTOP_X: PD2 */

#define ENDSTOP_Y_PORT GPIOA
#define ENDSTOP_Y_PIN 3u
/* ENDSTOP_Y: PA3 */

#define SERVO_PORT GPIOB
#define SERVO_PIN 6u
/* SERVO: PB6 */

#define I2C_SCL_PORT GPIOA
#define I2C_SCL_PIN 15u
/* I2C_SCL: PA15 */

#define I2C_SDA_PORT GPIOB
#define I2C_SDA_PIN 7u
/* I2C_SDA: PB7 */

#define BUZZER_PORT GPIOB
#define BUZZER_PIN 10u
/* BUZZER: PB10 */

#define LED_STAT1_PORT GPIOC
#define LED_STAT1_PIN 13u
/* LED_STAT1: PC13 */

#define LED_STAT2_PORT GPIOC
#define LED_STAT2_PIN 14u
/* LED_STAT2: PC14 */

#define LED_STAT3_PORT GPIOC
#define LED_STAT3_PIN 15u
/* LED_STAT3: PC15 */

#define LED_STAT4_PORT GPIOA
#define LED_STAT4_PIN 8u
/* LED_STAT4: PA8 */

#define USER_BTN_PORT GPIOB
#define USER_BTN_PIN 11u
/* USER_BTN: PB11 */

#define COMM_EN_PORT GPIOB
#define COMM_EN_PIN 15u
/* COMM_EN: PB15 */

#define MCU_TX_PORT GPIOA
#define MCU_TX_PIN 9u
/* MCU_TX: PA9 */

#define MCU_RX_PORT GPIOA
#define MCU_RX_PIN 10u
/* MCU_RX: PA10 */

#define USB_DM_MCU_PORT GPIOA
#define USB_DM_MCU_PIN 11u
/* USB_DM_MCU: PA11 */

#define USB_DP_MCU_PORT GPIOA
#define USB_DP_MCU_PIN 12u
/* USB_DP_MCU: PA12 */

#define SWDIO_PORT GPIOA
#define SWDIO_PIN 13u
/* SWDIO: PA13 */

#define SWCLK_PORT GPIOA
#define SWCLK_PIN 14u
/* SWCLK: PA14 */

#define CHG_STAT_PORT GPIOA
#define CHG_STAT_PIN 7u
/* CHG_STAT: PA7 */

#define PWR_KEY_PORT GPIOB
#define PWR_KEY_PIN 1u
/* PWR_KEY: PB1 */

#define MOT_ALARM_PORT GPIOB
#define MOT_ALARM_PIN 2u
/* MOT_ALARM: PB2 */

#define MOT_DIAG_PORT GPIOC
#define MOT_DIAG_PIN 4u
/* MOT_DIAG: PC4 */

#define ESP_EN_PORT GPIOB
#define ESP_EN_PIN 12u
/* ESP_EN: PB12 */

#define ESP_IO0_PORT GPIOB
#define ESP_IO0_PIN 13u
/* ESP_IO0: PB13 */

#define LED_COUNT 128u
/* zero-based 8x8 square index per chain position */
#define LED_CHAIN_SQ { \
    0u, 0u, 1u, 1u, 2u, 2u, 3u, 3u, 11u, 11u, 10u, 10u, 9u, 9u, 8u, 8u, \
    16u, 16u, 17u, 17u, 18u, 18u, 19u, 19u, 27u, 27u, 26u, 26u, 25u, 25u, 24u, 24u, \
    31u, 31u, 30u, 30u, 29u, 29u, 28u, 28u, 20u, 20u, 21u, 21u, 22u, 22u, 23u, 23u, \
    15u, 15u, 14u, 14u, 13u, 13u, 12u, 12u, 4u, 4u, 5u, 5u, 6u, 6u, 7u, 7u, \
    32u, 32u, 33u, 33u, 34u, 34u, 35u, 35u, 43u, 43u, 42u, 42u, 41u, 41u, 40u, 40u, \
    48u, 48u, 49u, 49u, 50u, 50u, 51u, 51u, 59u, 59u, 58u, 58u, 57u, 57u, 56u, 56u, \
    63u, 63u, 62u, 62u, 61u, 61u, 60u, 60u, 52u, 52u, 53u, 53u, 54u, 54u, 55u, 55u, \
    47u, 47u, 46u, 46u, 45u, 45u, 44u, 44u, 36u, 36u, 37u, 37u, 38u, 38u, 39u, 39u }
#define LED_COLOR_WHITE 0xFFAA3Cu
#define LED_COLOR_BLACK 0x283CFFu

#endif
