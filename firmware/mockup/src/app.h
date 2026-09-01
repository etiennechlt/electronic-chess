/* Module interfaces of the mockup firmware. */

#ifndef APP_H
#define APP_H

#include <stdbool.h>
#include <stdint.h>

#include "board.h"

/* clock.c */
void clock_init_170mhz(void);

/* uart.c: USART2 = ST-Link VCP (CSV and CLI), USART1 = Pi link. */
void uart_init(void);
void uart_putc(char c);
void uart_puts(const char *s);
void uart_put_uint(uint32_t v);
void uart_put_int(int32_t v);
int uart_getc_nonblock(void); /* -1 when empty */
void pi_uart_putc(char c);
int pi_uart_getc_nonblock(void);

/* adc.c: ADC1 IN1 (PA0) one-shot burst of ADC_SAMPLES via DMA. */
void adc_init(void);
void adc_capture_start(void);
bool adc_capture_done(void);
extern volatile uint16_t adc_buf[ADC_SAMPLES];
uint32_t adc_sample_rate_hz(void);

/* comp.c: COMP1 (PA1) against DAC3 threshold, captured by TIM2 CH4. */
void comp_init(void);
void comp_capture_arm(void);
uint32_t comp_capture_count(void);
uint32_t comp_capture_get(uint32_t idx);

/* fft.c: 512-point real FFT with Hann window and peak interpolation. */
void fft_init(void);
typedef struct {
    float freq_hz;
    float amplitude;
    float noise_floor;
} fft_peak_t;
fft_peak_t fft_peak(const volatile uint16_t *samples, uint32_t n,
                    uint32_t fs_hz, uint32_t f_lo_hz, uint32_t f_hi_hz);

/* measure.c */
typedef struct {
    uint32_t fa_hz;      /* path A: FFT peak */
    uint32_t fb_hz;      /* path B: comparator period, 0 if unusable */
    uint32_t amp_mv;     /* peak amplitude at the ADC, millivolts */
    uint32_t snr_db10;   /* 10 x SNR in dB */
} measure_t;
void measure_init(void);
measure_t measure_square(uint32_t square); /* 0..3 */
void measure_set_drive_pulse_ns(uint32_t ns);

/* led.c */
typedef enum { LED_CAMP_OFF = 0, LED_CAMP_WHITE, LED_CAMP_BLACK } led_camp_t;
void led_init(void);
void led_set_square(uint32_t square, led_camp_t camp); /* 0..3 */
void led_apply(void);
void led_all_off(void);

/* calib.c */
typedef struct {
    uint32_t magic;
    uint32_t freq_hz[N_SQUARES];
    uint32_t crc;
} calib_t;
bool calib_load(calib_t *out);
bool calib_store(const calib_t *cal);
int calib_classify(const calib_t *cal, uint32_t f_hz);

/* cli.c */
void cli_poll(void);

#endif
