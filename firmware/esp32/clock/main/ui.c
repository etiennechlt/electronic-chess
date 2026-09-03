/* ILI9341 2.4 inch panel on SPI2 through esp_lcd (ESP-IDF 5.x). The
 * digits are drawn as seven-segment bars so no font asset is needed;
 * small text uses the 8x8 glyph table below (digits, letters, a few
 * signs). Pins follow tools/boardgen/clock.py. */
#include "ui.h"

#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_lcd_ili9341.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"

#define PIN_SCK 15
#define PIN_MOSI 16
#define PIN_MISO 17
#define PIN_CS 4
#define PIN_DC 5
#define PIN_RST 6
#define PIN_BL 7

#define W 320
#define H 240
#define RGB(r, g, b) ((uint16_t)((((r) >> 3) << 11) | (((g) >> 2) << 5) | ((b) >> 3)))
#define C_BG RGB(0, 0, 0)
#define C_DIM RGB(70, 70, 70)
#define C_ON RGB(255, 255, 255)
#define C_ACTIVE RGB(60, 200, 90)
#define C_ALERT RGB(230, 60, 40)

static esp_lcd_panel_handle_t panel;
static uint16_t line_buf[W * 8];
static char status[16] = "";
static char last_move[8] = "";
static char battery[6] = "";
static char preset_label[8] = "";

static void fill(int x, int y, int w, int h, uint16_t color) {
    if (w <= 0 || h <= 0) {
        return;
    }
    for (int i = 0; i < W * 8; i++) {
        line_buf[i] = color;
    }
    for (int yy = y; yy < y + h; yy += 8) {
        int hh = (y + h - yy) < 8 ? (y + h - yy) : 8;
        esp_lcd_panel_draw_bitmap(panel, x, yy, x + w, yy + hh, line_buf);
    }
}

/* seven segments: a b c d e f g bits, bar thickness t, digit box w x h */
static const uint8_t SEG[11] = {0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f, 0x00};

static void digit(int x, int y, int w, int h, int t, int d, uint16_t on, uint16_t off) {
    uint8_t s = SEG[d < 0 || d > 9 ? 10 : d];
    int mid = y + h / 2 - t / 2;
    fill(x + t, y, w - 2 * t, t, s & 0x01 ? on : off);                 /* a */
    fill(x + w - t, y + t, t, h / 2 - t, s & 0x02 ? on : off);         /* b */
    fill(x + w - t, mid + t, t, h / 2 - t, s & 0x04 ? on : off);       /* c */
    fill(x + t, y + h - t, w - 2 * t, t, s & 0x08 ? on : off);         /* d */
    fill(x, mid + t, t, h / 2 - t, s & 0x10 ? on : off);               /* e */
    fill(x, y + t, t, h / 2 - t, s & 0x20 ? on : off);                 /* f */
    fill(x + t, mid, w - 2 * t, t, s & 0x40 ? on : off);               /* g */
}

/* "m:ss" / "mm:ss" / "h:mm:ss" / "0:ss.d" in a 150 px wide box */
static void time_box(int x, int y, const char *txt, uint16_t on) {
    int n = strlen(txt);
    int dw = n > 5 ? 18 : 26, dh = n > 5 ? 34 : 48, t = n > 5 ? 3 : 5, gap = 4;
    int cx = x;
    for (int i = 0; i < n; i++) {
        char c = txt[i];
        if (c == ':' || c == '.') {
            fill(cx + 2, y + dh / 3, t, t, on);
            fill(cx + 2, y + 2 * dh / 3, c == ':' ? t : 0, t, on);
            cx += t + 6;
        } else {
            digit(cx, y, dw, dh, t, c - '0', on, C_DIM);
            cx += dw + gap;
        }
    }
}

/* 5x7 glyphs for the footer, a subset that covers the protocol */
static const uint8_t FONT[][5] = {
    {0x7e, 0x11, 0x11, 0x11, 0x7e}, {0x7f, 0x49, 0x49, 0x49, 0x36}, {0x3e, 0x41, 0x41, 0x41, 0x22},
    {0x7f, 0x41, 0x41, 0x22, 0x1c}, {0x7f, 0x49, 0x49, 0x49, 0x41}, {0x7f, 0x09, 0x09, 0x01, 0x01},
    {0x3e, 0x41, 0x41, 0x51, 0x32}, {0x7f, 0x08, 0x08, 0x08, 0x7f}, {0x00, 0x41, 0x7f, 0x41, 0x00},
    {0x20, 0x40, 0x41, 0x3f, 0x01}, {0x7f, 0x08, 0x14, 0x22, 0x41}, {0x7f, 0x40, 0x40, 0x40, 0x40},
    {0x7f, 0x02, 0x04, 0x02, 0x7f}, {0x7f, 0x04, 0x08, 0x10, 0x7f}, {0x3e, 0x41, 0x41, 0x41, 0x3e},
    {0x7f, 0x09, 0x09, 0x09, 0x06}, {0x3e, 0x41, 0x51, 0x21, 0x5e}, {0x7f, 0x09, 0x19, 0x29, 0x46},
    {0x46, 0x49, 0x49, 0x49, 0x31}, {0x01, 0x01, 0x7f, 0x01, 0x01}, {0x3f, 0x40, 0x40, 0x40, 0x3f},
    {0x1f, 0x20, 0x40, 0x20, 0x1f}, {0x7f, 0x20, 0x18, 0x20, 0x7f}, {0x63, 0x14, 0x08, 0x14, 0x63},
    {0x03, 0x04, 0x78, 0x04, 0x03}, {0x61, 0x51, 0x49, 0x45, 0x43},
    {0x3e, 0x51, 0x49, 0x45, 0x3e}, {0x00, 0x42, 0x7f, 0x40, 0x00}, {0x42, 0x61, 0x51, 0x49, 0x46},
    {0x21, 0x41, 0x45, 0x4b, 0x31}, {0x18, 0x14, 0x12, 0x7f, 0x10}, {0x27, 0x45, 0x45, 0x45, 0x39},
    {0x3c, 0x4a, 0x49, 0x49, 0x30}, {0x01, 0x71, 0x09, 0x05, 0x03}, {0x36, 0x49, 0x49, 0x49, 0x36},
    {0x06, 0x49, 0x49, 0x29, 0x1e},
};

static void text(int x, int y, const char *s, uint16_t color) {
    for (; *s; s++, x += 12) {
        char c = *s;
        int idx = -1;
        if (c >= 'a' && c <= 'z') {
            idx = c - 'a';
        } else if (c >= 'A' && c <= 'Z') {
            idx = c - 'A';
        } else if (c >= '0' && c <= '9') {
            idx = 26 + (c - '0');
        }
        if (idx < 0) {
            continue;
        }
        for (int col = 0; col < 5; col++) {
            for (int row = 0; row < 7; row++) {
                if (FONT[idx][col] & (1 << row)) {
                    fill(x + col * 2, y + row * 2, 2, 2, color);
                }
            }
        }
    }
}

void ui_init(void) {
    spi_bus_config_t bus = {
        .sclk_io_num = PIN_SCK, .mosi_io_num = PIN_MOSI, .miso_io_num = PIN_MISO,
        .quadwp_io_num = -1, .quadhd_io_num = -1, .max_transfer_sz = W * 8 * 2,
    };
    spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    esp_lcd_panel_io_handle_t io;
    esp_lcd_panel_io_spi_config_t io_cfg = {
        .dc_gpio_num = PIN_DC, .cs_gpio_num = PIN_CS, .pclk_hz = 40 * 1000 * 1000,
        .lcd_cmd_bits = 8, .lcd_param_bits = 8, .spi_mode = 0, .trans_queue_depth = 10,
    };
    esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &io_cfg, &io);
    esp_lcd_panel_dev_config_t dev = {
        .reset_gpio_num = PIN_RST, .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_BGR,
        .bits_per_pixel = 16,
    };
    esp_lcd_new_panel_ili9341(io, &dev, &panel);
    esp_lcd_panel_reset(panel);
    esp_lcd_panel_init(panel);
    esp_lcd_panel_swap_xy(panel, true);
    esp_lcd_panel_mirror(panel, false, true);
    esp_lcd_panel_disp_on_off(panel, true);
    gpio_set_direction(PIN_BL, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_BL, 1);
    fill(0, 0, W, H, C_BG);
}

void ui_set_status(const char *s) { strncpy(status, s, sizeof status - 1); }
void ui_set_last_move(const char *s) { strncpy(last_move, s, sizeof last_move - 1); }
void ui_set_board_battery(const char *s) { strncpy(battery, s, sizeof battery - 1); }
void ui_set_preset(const char *s) { strncpy(preset_label, s, sizeof preset_label - 1); }

void ui_render(const chessclock_t *c, bool in_menu, bool linked) {
    static char shown[2][12] = {"", ""};
    static side_t shown_side = SIDE_WHITE;
    static int shown_state = -1;
    char t[2][12];
    clock_format(c->left_ms[0], t[0]);
    clock_format(c->left_ms[1], t[1]);
    bool side_changed = c->to_move != shown_side || (int)c->state != shown_state;
    for (int s = 0; s < 2; s++) {
        if (strcmp(t[s], shown[s]) != 0 || side_changed) {
            uint16_t color = C_ON;
            if (c->state == CLK_RUNNING && c->to_move == s) {
                color = C_ACTIVE;
            }
            if (c->left_ms[s] < 10000 || (c->state == CLK_FLAG && c->flagged == s)) {
                color = C_ALERT;
            }
            fill(s * 160 + 5, 60, 150, 50, C_BG);
            time_box(s * 160 + 5, 60, t[s], color);
            strcpy(shown[s], t[s]);
        }
    }
    if (side_changed) {
        fill(0, 20, W, 20, C_BG);
        text(20, 22, "BLANCS", c->to_move == SIDE_WHITE ? C_ACTIVE : C_DIM);
        text(180, 22, "NOIRS", c->to_move == SIDE_BLACK ? C_ACTIVE : C_DIM);
        shown_side = c->to_move;
        shown_state = (int)c->state;
    }
    /* footer: preset (highlighted in the menu), link, last move, battery */
    static uint32_t footer_hash;
    uint32_t h = 5381;
    const char *parts[] = {preset_label, last_move, battery, status, in_menu ? "m" : "", linked ? "l" : ""};
    for (size_t i = 0; i < sizeof parts / sizeof parts[0]; i++) {
        for (const char *p = parts[i]; *p; p++) {
            h = h * 33 + (uint8_t)*p;
        }
    }
    if (h != footer_hash) {
        fill(0, 150, W, 90, C_BG);
        text(20, 160, preset_label, in_menu ? C_ACTIVE : C_ON);
        text(20, 185, c->mode == MODE_FREE ? "LIBRE" : clock_mode_name(c->mode), C_DIM);
        text(180, 160, linked ? "PLATEAU OK" : "PLATEAU", linked ? C_ACTIVE : C_DIM);
        text(180, 185, last_move, C_ON);
        text(180, 210, battery, C_DIM);
        text(20, 210, status, C_DIM);
        footer_hash = h;
    }
}
