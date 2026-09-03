/* Per-coil measurement sequence on the quadrant front end (ADR 0010):
 * address the coil on the shared bus (mux, excitation and damping
 * decoders follow the same 4-bit index, split as A0..A2 plus the two
 * mux enables), broadband drive pulse from the shared rail, flyback,
 * active damping during the blanking window, then acquisition on the
 * quadrant's ADC (path A, FFT) and, on quadrant 1 only, the comparator
 * period capture (path B). The four quadrants are scanned one after the
 * other with their own ADC; the address bus is common. */

#include <math.h>

#include "app.h"

static uint32_t drive_pulse_ns = DRIVE_PULSE_NS;

void measure_set_drive_pulse_ns(uint32_t ns) {
    drive_pulse_ns = ns;
}

void measure_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                    RCC_AHB2ENR_GPIOCEN | RCC_AHB2ENR_GPIODEN;
    gpio_clear(PULSE_EN_PORT, PULSE_EN_PIN);
    gpio_out(PULSE_EN_PORT, PULSE_EN_PIN);
    gpio_set(DAMP_EN_N_PORT, DAMP_EN_N_PIN);  /* damping decoder disabled */
    gpio_out(DAMP_EN_N_PORT, DAMP_EN_N_PIN);
    gpio_clear(MUX_EN_L_PORT, MUX_EN_L_PIN);
    gpio_out(MUX_EN_L_PORT, MUX_EN_L_PIN);
    gpio_clear(MUX_EN_H_PORT, MUX_EN_H_PIN);
    gpio_out(MUX_EN_H_PORT, MUX_EN_H_PIN);
    gpio_out(MUX_A0_PORT, MUX_A0_PIN);
    gpio_out(MUX_A1_PORT, MUX_A1_PIN);
    gpio_out(MUX_A2_PORT, MUX_A2_PIN);
}

/* Coil index 0..15 on the shared bus: A0..A2 plus the half select, which
 * the decoders read as their fourth address bit (MUX_EN_H). */
static void bus_select(uint32_t coil) {
    gpio_write(MUX_A0_PORT, MUX_A0_PIN, coil & 1u);
    gpio_write(MUX_A1_PORT, MUX_A1_PIN, coil & 2u);
    gpio_write(MUX_A2_PORT, MUX_A2_PIN, coil & 4u);
    gpio_write(MUX_EN_H_PORT, MUX_EN_H_PIN, coil & 8u);
    gpio_write(MUX_EN_L_PORT, MUX_EN_L_PIN, !(coil & 8u));
}

static void bus_release(void) {
    gpio_clear(MUX_EN_L_PORT, MUX_EN_L_PIN);
    gpio_clear(MUX_EN_H_PORT, MUX_EN_H_PIN);
}

static uint32_t path_b_freq(void) {
    uint32_t n = comp_capture_count();
    if (n < 6u) {
        return 0u; /* not enough clean crossings */
    }
    uint32_t deltas[16];
    uint32_t m = (n - 1u < 16u) ? n - 1u : 16u;
    for (uint32_t i = 0; i < m; i++) {
        deltas[i] = comp_capture_get(i + 1u) - comp_capture_get(i);
    }
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

measure_t measure_coil(uint32_t quadrant, uint32_t coil) {
    measure_t out = {0};
    bool path_b = (quadrant == 0u);

    /* 1. Address the coil: mux input, excitation gate and damping FET
     *    all follow the bus; damping on while the rail settles. */
    bus_select(coil);
    gpio_clear(DAMP_EN_N_PORT, DAMP_EN_N_PIN);
    adc_select(quadrant);
    delay_ns(2000u);

    /* 2. Release the damping, energize the pulse rail (the excitation
     *    decoder is inhibited until PULSE_EN rises, so the gate and the
     *    rail switch on together). */
    gpio_set(DAMP_EN_N_PORT, DAMP_EN_N_PIN);
    delay_ns(300u);

    /* 3. Broadband current pulse through the addressed coil. */
    gpio_set(PULSE_EN_PORT, PULSE_EN_PIN);
    delay_ns(drive_pulse_ns);
    gpio_clear(PULSE_EN_PORT, PULSE_EN_PIN);
    delay_ns(400u); /* flyback into the SS34FL clamp */

    /* 4. Blanking: actively damp the sense coil, then release. */
    gpio_clear(DAMP_EN_N_PORT, DAMP_EN_N_PIN);
    delay_ns(BLANKING_NS);
    gpio_set(DAMP_EN_N_PORT, DAMP_EN_N_PIN);

    /* 5. Listen. */
    if (path_b) {
        comp_capture_arm();
    }
    adc_capture_start();
    while (!adc_capture_done()) {
    }

    /* 6. Re-damp, release the bus and process. */
    gpio_clear(DAMP_EN_N_PORT, DAMP_EN_N_PIN);
    bus_release();

    fft_peak_t peak = fft_peak(adc_buf, ADC_SAMPLES, adc_sample_rate_hz(),
                               BAND_LO_HZ, BAND_HI_HZ);
    out.fa_hz = (uint32_t)peak.freq_hz;
    out.fb_hz = path_b ? path_b_freq() : 0u;
    out.amp_mv = (uint32_t)(peak.amplitude * 3300.0f / 4096.0f);
    float snr = peak.amplitude / (peak.noise_floor + 1e-9f);
    float db10 = 100.0f * log10f(snr + 1e-9f) * 2.0f;
    out.snr_db10 = (db10 > 0.0f) ? (uint32_t)db10 : 0u;
    return out;
}

measure_t measure_square(uint32_t square) {
    return measure_coil(square / COILS_PER_QUADRANT, square % COILS_PER_QUADRANT);
}
