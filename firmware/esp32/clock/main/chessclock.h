/* Chess clock logic, independent of the hardware so it can be unit
 * tested on a PC (see test_chessclock.c). Times in milliseconds. */
#ifndef CHESSCLOCK_H
#define CHESSCLOCK_H

#include <stdbool.h>
#include <stdint.h>

typedef enum { MODE_FISCHER, MODE_BRONSTEIN, MODE_SIMPLE, MODE_FREE } clock_mode_t;
typedef enum { SIDE_WHITE = 0, SIDE_BLACK = 1 } side_t;
typedef enum { CLK_IDLE, CLK_RUNNING, CLK_PAUSED, CLK_FLAG } clock_state_t;

typedef struct {
    clock_mode_t mode;
    uint32_t base_ms;
    uint32_t increment_ms;
    int32_t left_ms[2];
    uint32_t move_start_ms;           /* Bronstein: when the current move began */
    side_t to_move;
    clock_state_t state;
    side_t flagged;
    uint32_t moves[2];
    bool warned_10s[2];
} chessclock_t;

void clock_init(chessclock_t *c, clock_mode_t mode, uint32_t base_s, uint32_t increment_s);
/* The side `side` presses its end of the rocker at time `now_ms`:
 * starts the clock on the first press, otherwise hands the move over. */
void clock_press(chessclock_t *c, side_t side, uint32_t now_ms);
void clock_pause_toggle(chessclock_t *c, uint32_t now_ms);
/* Advances the running side by `dt_ms`; returns true on a new event
 * (flag fall or 10 s warning) that deserves a beep. */
bool clock_tick(chessclock_t *c, uint32_t dt_ms, uint32_t now_ms);
/* Formats "mm:ss" (or "m:ss.d" under 10 s, "h:mm:ss" above an hour). */
void clock_format(int32_t ms, char out[12]);
const char *clock_mode_name(clock_mode_t mode);

#endif
