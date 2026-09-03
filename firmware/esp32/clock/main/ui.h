/* Display of the clock: two large times, the side to move, the preset,
 * the link state and a footer (last move, board battery). */
#ifndef UI_H
#define UI_H

#include <stdbool.h>

#include "chessclock.h"

void ui_init(void);
void ui_render(const chessclock_t *c, bool in_menu, bool linked);
void ui_set_status(const char *status);
void ui_set_last_move(const char *uci);
void ui_set_board_battery(const char *percent);
void ui_set_preset(const char *label);

#endif
