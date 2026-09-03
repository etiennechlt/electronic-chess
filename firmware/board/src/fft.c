/* Self-contained 512-point radix-2 FFT (float), Hann window, band
 * peak search with parabolic interpolation on log magnitudes. Slower
 * than CMSIS-DSP but dependency-free; the ~1 ms it costs per square
 * is irrelevant on the mockup. */

#include <math.h>

#include "app.h"

#define N 512u
#define LOG2N 9u

static float wr[N / 2u], wi[N / 2u], hann[N];
static float re[N], im[N];

void fft_init(void) {
    for (uint32_t k = 0; k < N / 2u; k++) {
        float a = -2.0f * (float)M_PI * (float)k / (float)N;
        wr[k] = cosf(a);
        wi[k] = sinf(a);
    }
    for (uint32_t n = 0; n < N; n++) {
        hann[n] = 0.5f - 0.5f * cosf(2.0f * (float)M_PI * (float)n / (float)(N - 1u));
    }
}

static void fft_run(void) {
    /* Bit-reversal permutation. */
    for (uint32_t i = 1, j = 0; i < N; i++) {
        uint32_t bit = N >> 1u;
        for (; j & bit; bit >>= 1u) {
            j ^= bit;
        }
        j |= bit;
        if (i < j) {
            float tr = re[i]; re[i] = re[j]; re[j] = tr;
            float ti = im[i]; im[i] = im[j]; im[j] = ti;
        }
    }
    for (uint32_t len = 2; len <= N; len <<= 1u) {
        uint32_t step = N / len;
        for (uint32_t i = 0; i < N; i += len) {
            for (uint32_t k = 0; k < len / 2u; k++) {
                uint32_t tw = k * step;
                float ur = re[i + k], ui = im[i + k];
                float vr = re[i + k + len / 2u] * wr[tw] -
                           im[i + k + len / 2u] * wi[tw];
                float vi = re[i + k + len / 2u] * wi[tw] +
                           im[i + k + len / 2u] * wr[tw];
                re[i + k] = ur + vr;
                im[i + k] = ui + vi;
                re[i + k + len / 2u] = ur - vr;
                im[i + k + len / 2u] = ui - vi;
            }
        }
    }
}

fft_peak_t fft_peak(const volatile uint16_t *samples, uint32_t n,
                    uint32_t fs_hz, uint32_t f_lo_hz, uint32_t f_hi_hz) {
    (void)n;
    float mean = 0.0f;
    for (uint32_t i = 0; i < N; i++) {
        mean += (float)samples[i];
    }
    mean /= (float)N;
    for (uint32_t i = 0; i < N; i++) {
        re[i] = ((float)samples[i] - mean) * hann[i];
        im[i] = 0.0f;
    }
    fft_run();

    float bin_hz = (float)fs_hz / (float)N;
    uint32_t k_lo = (uint32_t)((float)f_lo_hz / bin_hz);
    uint32_t k_hi = (uint32_t)((float)f_hi_hz / bin_hz);
    if (k_hi > N / 2u - 2u) {
        k_hi = N / 2u - 2u;
    }
    if (k_lo < 2u) {
        k_lo = 2u;
    }
    uint32_t kp = k_lo;
    float best = 0.0f, acc = 0.0f;
    for (uint32_t k = k_lo; k <= k_hi; k++) {
        float m = re[k] * re[k] + im[k] * im[k];
        acc += m;
        if (m > best) {
            best = m;
            kp = k;
        }
    }
    float m0 = logf(re[kp - 1u] * re[kp - 1u] + im[kp - 1u] * im[kp - 1u] + 1e-12f);
    float m1 = logf(best + 1e-12f);
    float m2 = logf(re[kp + 1u] * re[kp + 1u] + im[kp + 1u] * im[kp + 1u] + 1e-12f);
    float denom = m0 - 2.0f * m1 + m2;
    float delta = (denom != 0.0f) ? 0.5f * (m0 - m2) / denom : 0.0f;
    if (delta > 0.5f) {
        delta = 0.5f;
    }
    if (delta < -0.5f) {
        delta = -0.5f;
    }
    fft_peak_t out;
    out.freq_hz = ((float)kp + delta) * bin_hz;
    out.amplitude = sqrtf(best) * 2.0f / (float)N / 0.5f; /* Hann gain */
    out.noise_floor = sqrtf((acc - best) / (float)(k_hi - k_lo)) * 2.0f /
                      (float)N / 0.5f;
    return out;
}
