/* Per-square measurement sequence (brief 3.4):
 * select, release the damp switch, broadband drive pulse, flyback,
 * active damping during the blanking window, then simultaneous
 * acquisition on both extraction paths: ADC + FFT (A) and comparator
 * period capture (B). */

#include <math.h>

#include "app.h"

static uint32_t drive_pulse_ns = DRIVE_PULSE_NS;

void measure_set_drive_pulse_ns(uint32_t ns) {
    drive_pulse_ns = ns;
}

typedef struct {
    GPIO_TypeDef *port;
    uint32_t pin;
} pin_t;

static const pin_t drive_pins[N_SQUARES] = {
    {DRIVE_1_PORT, DRIVE_1_PIN}, {DRIVE_2_PORT, DRIVE_2_PIN},
    {DRIVE_3_PORT, DRIVE_3_PIN}, {DRIVE_4_PORT, DRIVE_4_PIN},
};
static const pin_t damp_pins[N_SQUARES] = {
    {DAMP_1_PORT, DAMP_1_PIN}, {DAMP_2_PORT, DAMP_2_PIN},
    {DAMP_3_PORT, DAMP_3_PIN}, {DAMP_4_PORT, DAMP_4_PIN},
};

void measure_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                    RCC_AHB2ENR_GPIOCEN;
    for (uint32_t i = 0; i < N_SQUARES; i++) {
        gpio_clear(drive_pins[i].port, drive_pins[i].pin);
        gpio_out(drive_pins[i].port, drive_pins[i].pin);
        gpio_clear(damp_pins[i].port, damp_pins[i].pin); /* low = damped */
        gpio_out(damp_pins[i].port, damp_pins[i].pin);
    }
    gpio_clear(PULSE_EN_PORT, PULSE_EN_PIN);
    gpio_out(PULSE_EN_PORT, PULSE_EN_PIN);
    gpio_set(MUX_INH_PORT, MUX_INH_PIN); /* inhibited at rest */
    gpio_out(MUX_INH_PORT, MUX_INH_PIN);
    gpio_out(MUX_A0_PORT, MUX_A0_PIN);
    gpio_out(MUX_A1_PORT, MUX_A1_PIN);
}

static void mux_select(uint32_t square) {
    if (square & 1u) {
        gpio_set(MUX_A0_PORT, MUX_A0_PIN);
    } else {
        gpio_clear(MUX_A0_PORT, MUX_A0_PIN);
    }
    if (square & 2u) {
        gpio_set(MUX_A1_PORT, MUX_A1_PIN);
    } else {
        gpio_clear(MUX_A1_PORT, MUX_A1_PIN);
    }
    gpio_clear(MUX_INH_PORT, MUX_INH_PIN);
}

static uint32_t path_b_freq(void) {
    uint32_t n = comp_capture_count();
    if (n < 6u) {
        return 0u; /* not enough clean crossings */
    }
    /* Median of successive rising-edge periods over the first captures,
     * where the ringdown amplitude is highest. */
    uint32_t deltas[16];
    uint32_t m = (n - 1u < 16u) ? n - 1u : 16u;
    for (uint32_t i = 0; i < m; i++) {
        deltas[i] = comp_capture_get(i + 1u) - comp_capture_get(i);
    }
    /* Insertion sort, m <= 16. */
    for (uint32_t i = 1; i < m; i++) {
        uint32_t v = deltas[i];
        uint32_t j = i;
        while (j > 0u && deltas[j - 1u] > v) {
            deltas[j] = deltas[j - 1u];
            j--;
        }
        deltas[j] = v;
    }
    uint32_t med = deltas[m / 2u];
    if (med == 0u) {
        return 0u;
    }
    return (uint32_t)(((uint64_t)SYSCLK_HZ + med / 2u) / med);
}

measure_t measure_square(uint32_t square) {
    measure_t out = {0};

    /* 1. All coils damped, select the target through the mux. */
    for (uint32_t i = 0; i < N_SQUARES; i++) {
        gpio_clear(damp_pins[i].port, damp_pins[i].pin);
    }
    mux_select(square);
    delay_ns(2000u);

    /* 2. Release the selected damp switch, energize the pulse rail. */
    gpio_set(damp_pins[square].port, damp_pins[square].pin);
    gpio_set(PULSE_EN_PORT, PULSE_EN_PIN);
    delay_ns(300u);

    /* 3. Broadband current pulse through the selected coil. */
    gpio_set(drive_pins[square].port, drive_pins[square].pin);
    delay_ns(drive_pulse_ns);
    gpio_clear(drive_pins[square].port, drive_pins[square].pin);
    delay_ns(400u); /* flyback into the SS34 clamp */
    gpio_clear(PULSE_EN_PORT, PULSE_EN_PIN);

    /* 4. Blanking: actively damp the sense coil, then release. */
    gpio_clear(damp_pins[square].port, damp_pins[square].pin);
    delay_ns(BLANKING_NS);
    gpio_set(damp_pins[square].port, damp_pins[square].pin);

    /* 5. Listen on both paths. */
    comp_capture_arm();
    adc_capture_start();
    while (!adc_capture_done()) {
    }

    /* 6. Re-damp and process. */
    gpio_clear(damp_pins[square].port, damp_pins[square].pin);
    gpio_set(MUX_INH_PORT, MUX_INH_PIN);

    fft_peak_t peak = fft_peak(adc_buf, ADC_SAMPLES, adc_sample_rate_hz(),
                               BAND_LO_HZ, BAND_HI_HZ);
    out.fa_hz = (uint32_t)peak.freq_hz;
    out.fb_hz = path_b_freq();
    out.amp_mv = (uint32_t)(peak.amplitude * 3300.0f / 4096.0f);
    float snr = peak.amplitude / (peak.noise_floor + 1e-9f);
    float db10 = 100.0f * log10f(snr + 1e-9f) * 2.0f;
    out.snr_db10 = (db10 > 0.0f) ? (uint32_t)db10 : 0u;
    return out;
}
