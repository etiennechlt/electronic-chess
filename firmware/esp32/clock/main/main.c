/* Rocker chess clock: two microswitches under the bar, an encoder for
 * the menus, a buzzer, a 2.4 inch SPI display and a BLE link to the
 * board's bridge (Nordic UART Service, central role). Pins follow
 * tools/boardgen/clock.py (ESP_PINS). Not compiled in CI, see
 * ../README.md. */
#include <stdio.h>
#include <string.h>

#include "chessclock.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nus.h"
#include "proto.h"
#include "ui.h"

#define PIN_SW_WHITE 12
#define PIN_SW_BLACK 13
#define PIN_ENC_A 9
#define PIN_ENC_B 10
#define PIN_ENC_SW 11
#define PIN_BUZZER 14

static const char *TAG = "clock";

typedef enum { EV_WHITE, EV_BLACK, EV_ENC_CW, EV_ENC_CCW, EV_ENC_PUSH } event_t;

static QueueHandle_t events;
static chessclock_t clk;
static proto_reader_t from_board;

/* presets shown in the menu: base seconds, increment seconds, mode */
static const struct { uint32_t base_s, inc_s; clock_mode_t mode; const char *label; } PRESETS[] = {
    {180, 2, MODE_FISCHER, "3+2"},   {300, 0, MODE_SIMPLE, "5+0"},
    {600, 0, MODE_SIMPLE, "10+0"},   {900, 10, MODE_FISCHER, "15+10"},
    {1800, 0, MODE_SIMPLE, "30+0"},  {5400, 30, MODE_FISCHER, "90+30"},
    {0, 0, MODE_FREE, "libre"},
};
static int preset = 3;

static uint32_t now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

/* ------------------------------------------------------------- inputs */

static void IRAM_ATTR on_gpio(void *arg) {
    event_t ev = (event_t)(intptr_t)arg;
    BaseType_t woken = pdFALSE;
    xQueueSendFromISR(events, &ev, &woken);
    if (woken) {
        portYIELD_FROM_ISR();
    }
}

static void IRAM_ATTR on_encoder(void *arg) {
    (void)arg;
    /* half-step decoding on the A edge: direction from B */
    event_t ev = gpio_get_level(PIN_ENC_B) ? EV_ENC_CW : EV_ENC_CCW;
    BaseType_t woken = pdFALSE;
    xQueueSendFromISR(events, &ev, &woken);
    if (woken) {
        portYIELD_FROM_ISR();
    }
}

static void inputs_init(void) {
    gpio_config_t in = {
        .pin_bit_mask = (1ull << PIN_SW_WHITE) | (1ull << PIN_SW_BLACK) | (1ull << PIN_ENC_A) |
                        (1ull << PIN_ENC_B) | (1ull << PIN_ENC_SW),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&in);
    gpio_set_intr_type(PIN_ENC_B, GPIO_INTR_DISABLE);
    gpio_install_isr_service(0);
    gpio_isr_handler_add(PIN_SW_WHITE, on_gpio, (void *)EV_WHITE);
    gpio_isr_handler_add(PIN_SW_BLACK, on_gpio, (void *)EV_BLACK);
    gpio_isr_handler_add(PIN_ENC_SW, on_gpio, (void *)EV_ENC_PUSH);
    gpio_isr_handler_add(PIN_ENC_A, on_encoder, NULL);
}

/* ------------------------------------------------------------- buzzer */

static void buzzer_init(void) {
    ledc_timer_config_t t = {
        .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_10_BIT,
        .timer_num = LEDC_TIMER_0, .freq_hz = 2700, .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&t);
    ledc_channel_config_t ch = {
        .gpio_num = PIN_BUZZER, .speed_mode = LEDC_LOW_SPEED_MODE, .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0, .duty = 0, .hpoint = 0,
    };
    ledc_channel_config(&ch);
}

static void beep(int times) {
    for (int i = 0; i < times; i++) {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 512);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        vTaskDelay(pdMS_TO_TICKS(120));
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        vTaskDelay(pdMS_TO_TICKS(80));
    }
}

/* --------------------------------------------------------------- link */

static void send_times(void) {
    char line[48];
    snprintf(line, sizeof line, "C,%ld,%ld,%c\n", (long)clk.left_ms[0], (long)clk.left_ms[1],
             clk.to_move == SIDE_WHITE ? 'w' : 'b');
    nus_central_send(line);
}

static void send_new_game(void) {
    char line[48];
    snprintf(line, sizeof line, "N,%s,%lu,%lu\n", clock_mode_name(clk.mode),
             (unsigned long)(clk.base_ms / 1000u), (unsigned long)(clk.increment_ms / 1000u));
    nus_central_send(line);
}

static void on_board_line(const char *line, void *ctx) {
    (void)ctx;
    proto_msg_t m;
    if (!proto_parse(line, &m)) {
        return;
    }
    switch (m.type) {
    case 'S':                          /* game state from the board */
        if (m.n >= 1) {
            ui_set_status(m.field[0]);
        }
        break;
    case 'M':                          /* a move was detected: show it */
        if (m.n >= 1) {
            ui_set_last_move(m.field[0]);
        }
        break;
    case 'P':
        if (m.n >= 3) {
            ui_set_board_battery(m.field[2]);
        }
        break;
    default:
        break;
    }
}

static void on_ble_rx(const uint8_t *data, size_t n, void *ctx) {
    proto_reader_feed(&from_board, data, n, on_board_line, ctx);
}

/* --------------------------------------------------------------- main */

static void apply_preset(void) {
    clock_init(&clk, PRESETS[preset].mode, PRESETS[preset].base_s, PRESETS[preset].inc_s);
    ui_set_preset(PRESETS[preset].label);
    send_new_game();
}

void app_main(void) {
    events = xQueueCreate(16, sizeof(event_t));
    inputs_init();
    buzzer_init();
    ui_init();
    nus_central_start(on_ble_rx, NULL);
    apply_preset();

    uint32_t last = now_ms(), last_sent = last;
    bool in_menu = false;
    for (;;) {
        event_t ev;
        while (xQueueReceive(events, &ev, 0)) {
            uint32_t t = now_ms();
            switch (ev) {
            case EV_WHITE:
            case EV_BLACK: {
                side_t s = ev == EV_WHITE ? SIDE_WHITE : SIDE_BLACK;
                clock_state_t before = clk.state;
                clock_press(&clk, s, t);
                if (clk.state != before || clk.to_move != s) {
                    char line[8];
                    snprintf(line, sizeof line, "T,%c\n", s == SIDE_WHITE ? 'w' : 'b');
                    nus_central_send(line);
                    send_times();
                }
                break;
            }
            case EV_ENC_PUSH:
                if (clk.state == CLK_IDLE || clk.state == CLK_FLAG) {
                    in_menu = !in_menu;
                    if (!in_menu) {
                        apply_preset();
                    }
                } else {
                    clock_pause_toggle(&clk, t);
                }
                break;
            case EV_ENC_CW:
            case EV_ENC_CCW:
                if (in_menu) {
                    int n = (int)(sizeof PRESETS / sizeof PRESETS[0]);
                    preset = (preset + (ev == EV_ENC_CW ? 1 : n - 1)) % n;
                    ui_set_preset(PRESETS[preset].label);
                }
                break;
            }
        }
        uint32_t t = now_ms();
        if (clock_tick(&clk, t - last, t)) {
            beep(clk.state == CLK_FLAG ? 3 : 1);
            if (clk.state == CLK_FLAG) {
                char line[16];
                snprintf(line, sizeof line, "R,%c,flag\n", clk.flagged == SIDE_WHITE ? 'w' : 'b');
                nus_central_send(line);
            }
        }
        last = t;
        if (t - last_sent >= 1000 && clk.state == CLK_RUNNING) {
            send_times();
            last_sent = t;
        }
        ui_render(&clk, in_menu, nus_central_connected());
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    (void)TAG;
}
