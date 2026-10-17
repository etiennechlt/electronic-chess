#include "hall.h"

#include <stdlib.h>

void hall_init(demo_hall_t *h) {
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        h->baseline[i] = DEMO_BASELINE_COUNTS;
        h->state[i] = HALL_EMPTY;
    }
    h->zeroed = false;
}

void hall_zero(demo_hall_t *h, const int16_t raw[DEMO_SITES]) {
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        h->baseline[i] = raw[i];
        h->state[i] = HALL_EMPTY;
    }
    h->zeroed = true;
}

int16_t hall_corrected(int16_t raw, int16_t ground_counts, int16_t rail_half_counts) {
    int32_t span = (int32_t)rail_half_counts - ground_counts;
    if (span <= 0) {
        return raw;   /* reference channels not read: the raw value stands */
    }
    int32_t v = ((int32_t)raw - ground_counts) * (int32_t)DEMO_RAIL_HALF_COUNTS / span;
    return (int16_t)(ground_counts + v);
}

int16_t hall_swing(const demo_hall_t *h, unsigned site, int16_t corrected) {
    return (int16_t)(corrected - h->baseline[site]);
}

float hall_swing_mt(int16_t swing) {
    return (float)swing * (float)DEMO_ADC_LSB_MV / (float)DEMO_SENSITIVITY_MV_PER_MT;
}

hall_state_t hall_update(demo_hall_t *h, unsigned site, int16_t swing) {
    int16_t mag = (int16_t)abs(swing);
    if (h->state[site] == HALL_EMPTY) {
        if (mag >= DEMO_ON_COUNTS) {
            h->state[site] = HALL_PRESENT;
        }
    } else if (mag < DEMO_OFF_COUNTS) {
        h->state[site] = HALL_EMPTY;
    }
    return h->state[site];
}

char hall_pole(int16_t swing) {
    if (abs(swing) < DEMO_OFF_COUNTS) {
        return '.';
    }
    return swing > 0 ? 'S' : 'N';
}
