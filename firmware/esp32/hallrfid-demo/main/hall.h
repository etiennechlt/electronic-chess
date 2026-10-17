/* Hall side of the demonstrator, independent of the hardware so it is
 * tested on a PC: baselines, swings, the ratiometric correction through
 * the mux's reference channels, the presence decision with hysteresis
 * and the pole facing the sensor. Numbers from demo_config.h, generated
 * from config/board.yaml. */
#ifndef HALL_H
#define HALL_H

#include <stdbool.h>
#include <stdint.h>

#include "demo_config.h"

typedef enum { HALL_EMPTY = 0, HALL_PRESENT } hall_state_t;

typedef struct {
    int16_t baseline[DEMO_SITES];
    hall_state_t state[DEMO_SITES];
    bool zeroed;
} demo_hall_t;

/* every baseline at the sensor's quiescent output until hall_zero */
void hall_init(demo_hall_t *h);
/* the current readings of the empty board become the baselines */
void hall_zero(demo_hall_t *h, const int16_t raw[DEMO_SITES]);
/* raw counts corrected so the switched rail reads its nominal half:
 * ground_counts and rail_half_counts are the mux reference channels */
int16_t hall_corrected(int16_t raw, int16_t ground_counts, int16_t rail_half_counts);
/* corrected counts minus the baseline of the site */
int16_t hall_swing(const demo_hall_t *h, unsigned site, int16_t corrected);
/* the swing in millitesla at the sensor (sensitivity of the yaml) */
float hall_swing_mt(int16_t swing);
/* presence with hysteresis (on and off thresholds of the yaml); updates
 * and returns the state of the site */
hall_state_t hall_update(demo_hall_t *h, unsigned site, int16_t swing);
/* 'S' when a south pole faces the package (output up), 'N' for north,
 * '.' when the swing is under the release threshold */
char hall_pole(int16_t swing);

#endif
