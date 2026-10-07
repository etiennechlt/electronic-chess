/* See hallscan.h. Pure C99, no platform dependency. */
#include "hallscan.h"

#include <string.h>

void hallscan_init(hallscan_t *h, const hallscan_cfg_t *cfg, int16_t baseline_counts) {
    memset(h, 0, sizeof *h);
    h->cfg = *cfg;
    if (h->cfg.debounce_scans == 0) {
        h->cfg.debounce_scans = 1;
    }
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        h->baseline[i] = baseline_counts;
        h->last[i] = baseline_counts;
    }
}

void hallscan_zero(hallscan_t *h, const int16_t raw[HALL_SQUARES]) {
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        h->baseline[i] = raw[i];
        h->last[i] = raw[i];
        h->state[i] = HALL_EMPTY;
        h->pending[i] = HALL_EMPTY;
        h->agree[i] = 0;
    }
}

static hall_state_t classify(const hallscan_t *h, hall_state_t current, int16_t swing) {
    int32_t mag = swing < 0 ? -(int32_t)swing : (int32_t)swing;
    bool present;
    if (current == HALL_EMPTY) {
        present = mag >= h->cfg.on_counts;
    } else {
        present = mag >= h->cfg.off_counts;   /* hysteresis: stays until below off */
    }
    if (!present) {
        return HALL_EMPTY;
    }
    if (!h->cfg.color_by_polarity) {
        return HALL_PRESENT;
    }
    bool positive = swing > 0;
    return (positive == h->cfg.white_positive) ? HALL_WHITE : HALL_BLACK;
}

bool hallscan_update(hallscan_t *h, uint8_t square, int16_t raw, hall_event_t *ev) {
    if (square >= HALL_SQUARES) {
        return false;
    }
    int32_t swing32 = (int32_t)raw - (int32_t)h->baseline[square];
    if (swing32 > INT16_MAX) {
        swing32 = INT16_MAX;
    } else if (swing32 < -INT16_MAX) {
        swing32 = -INT16_MAX;
    }
    int16_t swing = (int16_t)swing32;
    h->last[square] = raw;
    hall_state_t current = h->state[square];
    hall_state_t seen = classify(h, current, swing);
    if (seen == current) {
        h->pending[square] = current;
        h->agree[square] = 0;
        return false;
    }
    if (seen != h->pending[square]) {
        h->pending[square] = seen;
        h->agree[square] = 1;
    } else if (h->agree[square] < 255) {
        h->agree[square]++;
    }
    if (h->agree[square] < h->cfg.debounce_scans) {
        return false;
    }
    h->state[square] = seen;
    h->agree[square] = 0;
    h->changes++;
    if (ev != NULL) {
        ev->square = square;
        ev->from = current;
        ev->to = seen;
        ev->swing = swing;
    }
    return true;
}

char hallscan_state_char(hall_state_t s) {
    switch (s) {
    case HALL_EMPTY:
        return '.';
    case HALL_WHITE:
        return 'w';
    case HALL_BLACK:
        return 'b';
    case HALL_PRESENT:
    default:
        return '?';
    }
}

void hallscan_board_line(const hallscan_t *h, char out[HALL_LINE_LEN]) {
    out[0] = 'B';
    out[1] = ',';
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        out[2 + i] = hallscan_state_char(h->state[i]);
    }
    out[2 + HALL_SQUARES] = '\0';
}

unsigned hallscan_count(const hallscan_t *h, hall_state_t s) {
    unsigned n = 0;
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        if (h->state[i] == s) {
            n++;
        }
    }
    return n;
}
