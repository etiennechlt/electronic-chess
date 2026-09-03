#include "chessclock.h"

#include <stdio.h>

void clock_init(chessclock_t *c, clock_mode_t mode, uint32_t base_s, uint32_t increment_s) {
    c->mode = mode;
    c->base_ms = base_s * 1000u;
    c->increment_ms = increment_s * 1000u;
    c->left_ms[0] = c->left_ms[1] = (int32_t)c->base_ms;
    c->to_move = SIDE_WHITE;
    c->state = CLK_IDLE;
    c->moves[0] = c->moves[1] = 0;
    c->warned_10s[0] = c->warned_10s[1] = false;
    c->move_start_ms = 0;
}

void clock_press(chessclock_t *c, side_t side, uint32_t now_ms) {
    if (c->state == CLK_FLAG) {
        return;
    }
    if (c->state == CLK_IDLE) {
        /* the side that presses first has just moved: the other side starts */
        c->to_move = side == SIDE_WHITE ? SIDE_BLACK : SIDE_WHITE;
        c->state = CLK_RUNNING;
        c->move_start_ms = now_ms;
        return;
    }
    if (c->state == CLK_PAUSED || side != c->to_move) {
        return;                       /* the wrong side pressed: ignored */
    }
    switch (c->mode) {
    case MODE_FISCHER:
        c->left_ms[side] += (int32_t)c->increment_ms;
        break;
    case MODE_BRONSTEIN: {
        uint32_t used = now_ms - c->move_start_ms;
        c->left_ms[side] += (int32_t)(used < c->increment_ms ? used : c->increment_ms);
        break;
    }
    default:
        break;
    }
    c->moves[side]++;
    c->to_move = side == SIDE_WHITE ? SIDE_BLACK : SIDE_WHITE;
    c->move_start_ms = now_ms;
}

void clock_pause_toggle(chessclock_t *c, uint32_t now_ms) {
    if (c->state == CLK_RUNNING) {
        c->state = CLK_PAUSED;
    } else if (c->state == CLK_PAUSED) {
        c->state = CLK_RUNNING;
        c->move_start_ms = now_ms;
    }
}

bool clock_tick(chessclock_t *c, uint32_t dt_ms, uint32_t now_ms) {
    (void)now_ms;
    if (c->state != CLK_RUNNING || c->mode == MODE_FREE) {
        return false;
    }
    side_t s = c->to_move;
    c->left_ms[s] -= (int32_t)dt_ms;
    if (c->left_ms[s] <= 0) {
        c->left_ms[s] = 0;
        c->state = CLK_FLAG;
        c->flagged = s;
        return true;
    }
    if (c->left_ms[s] <= 10000 && !c->warned_10s[s]) {
        c->warned_10s[s] = true;
        return true;
    }
    return false;
}

void clock_format(int32_t ms, char out[12]) {
    if (ms < 0) {
        ms = 0;
    }
    uint32_t s = (uint32_t)ms / 1000u;
    if (ms < 10000) {
        snprintf(out, 12, "%u:%02u.%u", 0u, s, ((uint32_t)ms / 100u) % 10u);
    } else if (s >= 3600) {
        snprintf(out, 12, "%u:%02u:%02u", s / 3600u, (s / 60u) % 60u, s % 60u);
    } else {
        snprintf(out, 12, "%u:%02u", s / 60u, s % 60u);
    }
}

const char *clock_mode_name(clock_mode_t mode) {
    switch (mode) {
    case MODE_FISCHER: return "fischer";
    case MODE_BRONSTEIN: return "bronstein";
    case MODE_SIMPLE: return "simple";
    default: return "free";
    }
}
