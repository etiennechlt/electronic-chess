/* Generated from config/board.yaml by scripts/gen_config.py. Do not edit. */
#ifndef DEMO_CONFIG_H
#define DEMO_CONFIG_H

/* DRV5055A3: 0.757 mV per ADC count, 15 mV/mT, pitch 50 mm */
#define DEMO_SENSOR "DRV5055A3"
#define DEMO_ADC_LSB_MV 0.7568
#define DEMO_SENSITIVITY_MV_PER_MT 15
#define DEMO_BASELINE_COUNTS 2180
#define DEMO_RAIL_HALF_COUNTS 2180
#define DEMO_ON_COUNTS 205
#define DEMO_OFF_COUNTS 143
#define DEMO_WEAKEST_PRESENT_COUNTS 410
#define DEMO_ADC_FULL_SCALE_MV 3100u
#define DEMO_SAMPLES 8u

/* timing from hallrfid_mockup.hall_chain: ROW_EN to a valid reading, and the
 * mux settling after the worst kick of its common node */
#define DEMO_ROW_ON_US 417u
#define DEMO_MUX_SETTLE_US 34u

/* ESP32-S3-WROOM-1-N8 GPIO numbers (hall_rfid.demo.esp32.pins) */
#define DEMO_PIN_MUX_OUT 1
#define DEMO_PIN_HALL_A1 2
#define DEMO_PIN_HALL_B1 4
#define DEMO_PIN_PICKUP 5
#define DEMO_PIN_LED 8
#define DEMO_PIN_RFID_IRQ 9
#define DEMO_PIN_ROW_EN1 10
#define DEMO_PIN_SPI_MOSI 11
#define DEMO_PIN_SPI_SCK 12
#define DEMO_PIN_SPI_MISO 13
#define DEMO_PIN_NSS_A1 14
#define DEMO_PIN_MUX_S0 15
#define DEMO_PIN_MUX_S1 16
#define DEMO_PIN_MUX_S2 17
#define DEMO_PIN_MUX_S3 18
#define DEMO_PIN_USB_DM 19
#define DEMO_PIN_USB_DP 20
#define DEMO_PIN_NRSTPD_A1 21
#define DEMO_PIN_NSS_B1 38
#define DEMO_PIN_UART0_TX 43
#define DEMO_PIN_UART0_RX 44
#define DEMO_PIN_NRSTPD_B1 47

/* the sensor sites: mux channel, name, whether a direct ADC input doubles it */
#define DEMO_SITES 6u
#define DEMO_SITE_CHANNEL {0u, 1u, 4u, 5u, 6u, 7u}
#define DEMO_SITE_NAME {"A1", "B1", "A1_sw", "A1_se", "A1_nw", "A1_ne"}
#define DEMO_SITE_DIRECT_PIN {2, 4, -1, -1, -1, -1}
#define DEMO_CH_GROUND 8u
#define DEMO_CH_RAIL_HALF 9u
#define DEMO_CH_LED_STEP 10u

/* the readers, in square order: NSS and NRSTPD pins */
#define DEMO_READERS 2u
#define DEMO_READER_NAME {"A1", "B1"}
#define DEMO_READER_NSS {14, 38}
#define DEMO_READER_NRSTPD {21, 47}

/* bring-up criteria the console prints (hall_rfid.mockup) */
#define DEMO_R_SENSE_OHM 1
#define DEMO_I_TVDD_ACCEPT_MA 70
#define DEMO_I_IDLE_MA 13.5
#define DEMO_I_IDLE_MAX_MA 19
#define DEMO_HALL_I_MA 6
#define DEMO_HALL_I_MAX_MA 10
#define DEMO_NXP_VERSION {0x91, 0x92}
#define DEMO_READ_TRIALS 100u
#define DEMO_READ_TRIALS_CONFIRM 300u

#endif
