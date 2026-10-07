/* Generated from config/board.yaml by scripts/gen_config.py. Do not edit. */
#ifndef HALLSCAN_CONFIG_H
#define HALLSCAN_CONFIG_H

#define HALL_SENSOR "DRV5053OA"
/* ADC counts: 0.757 mV per LSB, 11 mV/mT */
#define HALL_BASELINE_COUNTS 1348
#define HALL_ON_COUNTS 150
#define HALL_OFF_COUNTS 105
#define HALL_WEAKEST_PRESENT_COUNTS 300
#define HALL_STRONGEST_LIFTED_COUNTS 55
#define HALL_DEBOUNCE_SCANS 3u
#define HALL_COLOR_BY_POLARITY 0
#define HALL_WHITE_POSITIVE 1   /* which pole faces down: set at calibration */

/* scan: one mux per quadrant, sensor supply switched per row of each quadrant */
#define HALL_MUX_COUNT 4u
#define HALL_MUX_CHANNELS 16u
#define HALL_GROUPS 4u
#define HALL_SAMPLES_PER_SQUARE 8u
#define HALL_MUX_SETTLE_US 2u
#define HALL_POWER_ON_US 100u
#define HALL_ADC_FULL_SCALE_MV 3100u

/* ESP32-S3-WROOM-1 GPIO numbers */
#define HALL_PIN_ADC_Q1 1
#define HALL_PIN_ADC_Q2 2
#define HALL_PIN_ADC_Q3 3
#define HALL_PIN_ADC_Q4 4
#define HALL_PIN_MUX_S0 5
#define HALL_PIN_MUX_S1 6
#define HALL_PIN_MUX_S2 7
#define HALL_PIN_MUX_S3 8
#define HALL_PIN_ROW_EN0 9
#define HALL_PIN_ROW_EN1 10
#define HALL_PIN_ROW_EN2 11
#define HALL_PIN_ROW_EN3 12

/* board square (file + 8 * rank, a1 = 0) per mux and channel */
#define HALL_SQUARE_OF { \
    {0u, 1u, 2u, 3u, 8u, 9u, 10u, 11u, 16u, 17u, 18u, 19u, 24u, 25u, 26u, 27u}, \
    {4u, 5u, 6u, 7u, 12u, 13u, 14u, 15u, 20u, 21u, 22u, 23u, 28u, 29u, 30u, 31u}, \
    {32u, 33u, 34u, 35u, 40u, 41u, 42u, 43u, 48u, 49u, 50u, 51u, 56u, 57u, 58u, 59u}, \
    {36u, 37u, 38u, 39u, 44u, 45u, 46u, 47u, 52u, 53u, 54u, 55u, 60u, 61u, 62u, 63u} }

#endif
