/* Hall presence scanner, independent of the hardware so it can be unit
 * tested on a PC (test/test_hallscan.c). One analog Hall sensor per
 * square reads the piece's ferrite magnet; this module turns raw ADC
 * counts into a debounced occupancy map and the `B` line of the protocol
 * (docs/notes/12-protocole.md). Thresholds come from hallscan_config.h,
 * generated from config/board.yaml. */
#ifndef HALLSCAN_H
#define HALLSCAN_H

#include <stdbool.h>
#include <stdint.h>

#define HALL_SQUARES 64u
#define HALL_LINE_LEN (2u + HALL_SQUARES + 1u)   /* "B," + 64 squares + NUL */

typedef enum { HALL_EMPTY = 0, HALL_PRESENT, HALL_WHITE, HALL_BLACK } hall_state_t;

typedef struct {
    int16_t on_counts;        /* |raw - baseline| at or above this: present */
    int16_t off_counts;       /* below this: empty (hysteresis band in between) */
    uint8_t debounce_scans;   /* consecutive agreeing scans before a change is published */
    bool color_by_polarity;   /* the sign of the swing names the camp */
    bool white_positive;      /* white pieces swing the output up (set at calibration) */
} hallscan_cfg_t;

typedef struct {
    uint8_t square;           /* file + 8 * rank, a1 = 0 */
    hall_state_t from;
    hall_state_t to;
    int16_t swing;            /* raw minus baseline, counts */
} hall_event_t;

typedef struct {
    hallscan_cfg_t cfg;
    int16_t baseline[HALL_SQUARES];
    int16_t last[HALL_SQUARES];
    hall_state_t state[HALL_SQUARES];
    hall_state_t pending[HALL_SQUARES];
    uint8_t agree[HALL_SQUARES];
    uint32_t changes;
} hallscan_t;

/* Every square empty, every baseline at `baseline_counts` (the sensor's
 * quiescent output) until hallscan_zero measures the real ones. */
void hallscan_init(hallscan_t *h, const hallscan_cfg_t *cfg, int16_t baseline_counts);
/* Takes the current raw readings of an empty board as the baselines. */
void hallscan_zero(hallscan_t *h, const int16_t raw[HALL_SQUARES]);
/* Feeds one reading; returns true when the square's published state
 * changes, with the change in `ev`. */
bool hallscan_update(hallscan_t *h, uint8_t square, int16_t raw, hall_event_t *ev);
/* The protocol's occupancy line: 'B', ',', then one character per square
 * from a1 to h8: '.' empty, 'w' white, 'b' black, '?' present. */
void hallscan_board_line(const hallscan_t *h, char out[HALL_LINE_LEN]);
char hallscan_state_char(hall_state_t s);
unsigned hallscan_count(const hallscan_t *h, hall_state_t s);

#endif
