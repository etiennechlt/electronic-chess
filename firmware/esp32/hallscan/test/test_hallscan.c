/* Host-side test of the Hall scanner: see ../README.md for the command. */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "hallscan.h"
#include "hallscan_config.h"

static void feed_scans(hallscan_t *h, uint8_t sq, int16_t raw, int n, int *published) {
    hall_event_t ev;
    for (int i = 0; i < n; i++) {
        if (hallscan_update(h, sq, raw, &ev)) {
            (*published)++;
        }
    }
}

int main(void) {
    hallscan_t h;
    hall_event_t ev;
    char line[HALL_LINE_LEN];
    hallscan_cfg_t cfg = {
        .on_counts = HALL_ON_COUNTS,
        .off_counts = HALL_OFF_COUNTS,
        .debounce_scans = HALL_DEBOUNCE_SCANS,
        .color_by_polarity = false,
        .white_positive = true,
    };
    assert(HALL_OFF_COUNTS < HALL_ON_COUNTS);
    assert(HALL_DEBOUNCE_SCANS >= 1);

    hallscan_init(&h, &cfg, HALL_BASELINE_COUNTS);
    hallscan_board_line(&h, line);
    assert(strlen(line) == HALL_SQUARES + 2 && line[0] == 'B' && line[1] == ',');
    assert(line[2] == '.' && line[65] == '.');
    assert(hallscan_count(&h, HALL_EMPTY) == HALL_SQUARES);

    /* a pawn on e2 (square 12): the swing of the yaml's weakest present
     * field is well above the threshold, published after the debounce */
    int published = 0;
    int16_t pawn = (int16_t)(HALL_BASELINE_COUNTS + HALL_WEAKEST_PRESENT_COUNTS);
    feed_scans(&h, 12, pawn, HALL_DEBOUNCE_SCANS - 1, &published);
    assert(published == 0 && h.state[12] == HALL_EMPTY);
    assert(hallscan_update(&h, 12, pawn, &ev));
    assert(ev.square == 12 && ev.from == HALL_EMPTY && ev.to == HALL_PRESENT);
    assert(ev.swing == HALL_WEAKEST_PRESENT_COUNTS);
    hallscan_board_line(&h, line);
    assert(line[2 + 12] == '?' && hallscan_count(&h, HALL_PRESENT) == 1);

    /* hysteresis: a reading between off and on keeps the piece */
    int16_t between = (int16_t)(HALL_BASELINE_COUNTS + (HALL_ON_COUNTS + HALL_OFF_COUNTS) / 2);
    feed_scans(&h, 12, between, 10, &published);
    assert(published == 0 && h.state[12] == HALL_PRESENT);

    /* a bounce shorter than the debounce never publishes */
    feed_scans(&h, 12, HALL_BASELINE_COUNTS, HALL_DEBOUNCE_SCANS - 1, &published);
    assert(published == 0 && h.state[12] == HALL_PRESENT);
    feed_scans(&h, 12, pawn, 1, &published);
    assert(published == 0 && h.agree[12] == 0);

    /* lifted by lift_detect_mm: the king's residual field reads empty */
    int16_t lifted = (int16_t)(HALL_BASELINE_COUNTS + HALL_STRONGEST_LIFTED_COUNTS);
    assert(HALL_STRONGEST_LIFTED_COUNTS < HALL_OFF_COUNTS);
    feed_scans(&h, 12, lifted, HALL_DEBOUNCE_SCANS, &published);
    assert(published == 1 && h.state[12] == HALL_EMPTY && h.changes == 2);

    /* a negative swing (other pole down) is still a piece without polarity */
    int16_t flipped = (int16_t)(HALL_BASELINE_COUNTS - HALL_WEAKEST_PRESENT_COUNTS);
    feed_scans(&h, 63, flipped, HALL_DEBOUNCE_SCANS, &published);
    assert(h.state[63] == HALL_PRESENT);

    /* with polarity the sign names the camp, and the zero resets */
    cfg.color_by_polarity = true;
    hallscan_init(&h, &cfg, HALL_BASELINE_COUNTS);
    feed_scans(&h, 0, pawn, HALL_DEBOUNCE_SCANS, &published);
    feed_scans(&h, 7, flipped, HALL_DEBOUNCE_SCANS, &published);
    hallscan_board_line(&h, line);
    assert(line[2] == 'w' && line[2 + 7] == 'b');
    assert(strncmp(line, "B,w......b", 10) == 0);
    cfg.white_positive = false;
    hallscan_init(&h, &cfg, HALL_BASELINE_COUNTS);
    feed_scans(&h, 0, pawn, HALL_DEBOUNCE_SCANS, &published);
    assert(h.state[0] == HALL_BLACK);
    int16_t raw[HALL_SQUARES];
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        raw[i] = (int16_t)(HALL_BASELINE_COUNTS + 20);   /* offsets of real sensors */
    }
    hallscan_zero(&h, raw);
    assert(h.state[0] == HALL_EMPTY && h.baseline[5] == HALL_BASELINE_COUNTS + 20);
    assert(!hallscan_update(&h, 64, pawn, &ev));          /* out of range is ignored */

    /* the generated mapping covers the 64 squares once */
    static const uint8_t square_of[HALL_MUX_COUNT][HALL_MUX_CHANNELS] = HALL_SQUARE_OF;
    unsigned seen[HALL_SQUARES] = {0};
    for (unsigned m = 0; m < HALL_MUX_COUNT; m++) {
        for (unsigned c = 0; c < HALL_MUX_CHANNELS; c++) {
            assert(square_of[m][c] < HALL_SQUARES);
            seen[square_of[m][c]]++;
        }
    }
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        assert(seen[i] == 1);
    }
    assert(HALL_MUX_CHANNELS % HALL_GROUPS == 0);
    puts("hallscan ok");
    return 0;
}
