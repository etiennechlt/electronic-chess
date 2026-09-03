/* Host-side test of the clock logic: cc -I../main test_chessclock.c ../main/chessclock.c */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "chessclock.h"

int main(void) {
    chessclock_t c;
    char s[12];
    clock_init(&c, MODE_FISCHER, 180, 2);
    assert(c.state == CLK_IDLE);
    clock_press(&c, SIDE_WHITE, 0);          /* white moved first: black to move */
    assert(c.state == CLK_RUNNING && c.to_move == SIDE_BLACK);
    clock_tick(&c, 5000, 5000);
    assert(c.left_ms[SIDE_BLACK] == 175000 && c.left_ms[SIDE_WHITE] == 180000);
    clock_press(&c, SIDE_WHITE, 5000);       /* wrong side: ignored */
    assert(c.to_move == SIDE_BLACK);
    clock_press(&c, SIDE_BLACK, 5000);       /* black moved: +2 s */
    assert(c.left_ms[SIDE_BLACK] == 177000 && c.to_move == SIDE_WHITE);
    clock_format(c.left_ms[SIDE_BLACK], s);
    assert(strcmp(s, "2:57") == 0);
    clock_format(9500, s);
    assert(strcmp(s, "0:09.5") == 0);
    clock_format(3661000, s);
    assert(strcmp(s, "1:01:01") == 0);

    clock_init(&c, MODE_BRONSTEIN, 60, 5);
    clock_press(&c, SIDE_BLACK, 0);          /* white to move from t = 0 */
    clock_tick(&c, 2000, 2000);
    clock_press(&c, SIDE_WHITE, 2000);       /* used 2 s, gets 2 s back */
    assert(c.left_ms[SIDE_WHITE] == 60000);
    clock_tick(&c, 9000, 11000);
    clock_press(&c, SIDE_BLACK, 11000);      /* used 9 s, capped at 5 s back */
    assert(c.left_ms[SIDE_BLACK] == 56000);

    clock_init(&c, MODE_SIMPLE, 1, 0);
    clock_press(&c, SIDE_BLACK, 0);
    assert(clock_tick(&c, 100, 100) == true);   /* 10 s warning fires right away */
    assert(clock_tick(&c, 1000, 1100) == true); /* flag */
    assert(c.state == CLK_FLAG && c.flagged == SIDE_WHITE && c.left_ms[SIDE_WHITE] == 0);
    clock_press(&c, SIDE_WHITE, 2000);       /* after the flag nothing moves */
    assert(c.state == CLK_FLAG);
    puts("chessclock ok");
    return 0;
}
