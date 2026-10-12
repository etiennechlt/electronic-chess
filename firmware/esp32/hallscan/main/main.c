/* Standalone Hall presence scanner of note 24 on an ESP32-S3: four
 * CD74HC4067 (one per quadrant, address lines shared) bring 64 analog
 * Hall sensors to four ADC1 inputs; the sensor supply is switched per
 * row of each quadrant to keep the average current down. Publishes the
 * `B` occupancy line of docs/notes/12-protocole.md on every change, and
 * answers three console letters: `z` (zero: take the empty board as the
 * baseline), `r` (raw counts, CSV), `b` (the current `B` line).
 *
 * Not compiled in CI (no ESP-IDF toolchain), see ../README.md; the
 * scanner logic itself (hallscan.c) is tested on the host. */
#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "hallscan.h"
#include "hallscan_config.h"

#define CONSOLE_PORT UART_NUM_0
#define SCAN_PERIOD_MS 10        /* about 100 scans per second, debounced in hallscan */

static const char *TAG = "hallscan";
static const int ADC_GPIO[HALL_MUX_COUNT] = {HALL_PIN_ADC_Q1, HALL_PIN_ADC_Q2, HALL_PIN_ADC_Q3,
                                             HALL_PIN_ADC_Q4};
static const int ADDR_GPIO[4] = {HALL_PIN_MUX_S0, HALL_PIN_MUX_S1, HALL_PIN_MUX_S2,
                                 HALL_PIN_MUX_S3};
static const int ROW_GPIO[HALL_GROUPS] = {HALL_PIN_ROW_EN0, HALL_PIN_ROW_EN1, HALL_PIN_ROW_EN2,
                                          HALL_PIN_ROW_EN3};
static const uint8_t SQUARE_OF[HALL_MUX_COUNT][HALL_MUX_CHANNELS] = HALL_SQUARE_OF;

static adc_oneshot_unit_handle_t adc;
static adc_channel_t adc_chan[HALL_MUX_COUNT];
static hallscan_t scanner;
static int16_t raw_counts[HALL_SQUARES];

static void emit(const char *line) {
    uart_write_bytes(CONSOLE_PORT, line, strlen(line));
    uart_write_bytes(CONSOLE_PORT, "\n", 1);
}

static void emit_board(void) {
    char line[HALL_LINE_LEN];
    hallscan_board_line(&scanner, line);
    emit(line);
}

static void emit_raw(void) {
    char line[8 + HALL_SQUARES * 6];
    int n = snprintf(line, sizeof line, "R");
    for (unsigned i = 0; i < HALL_SQUARES; i++) {
        n += snprintf(line + n, sizeof line - (size_t)n, ",%d", raw_counts[i]);
    }
    emit(line);
}

static void select_channel(unsigned channel) {
    for (int bit = 0; bit < 4; bit++) {
        gpio_set_level(ADDR_GPIO[bit], (channel >> bit) & 1u);
    }
}

static void power_group(unsigned group) {
    for (unsigned g = 0; g < HALL_GROUPS; g++) {
        gpio_set_level(ROW_GPIO[g], g == group ? 0 : 1);   /* active low: P-FET gate */
    }
}

static int16_t read_average(unsigned mux) {
    int32_t sum = 0;
    for (unsigned s = 0; s < HALL_SAMPLES_PER_SQUARE; s++) {
        int value = 0;
        ESP_ERROR_CHECK(adc_oneshot_read(adc, adc_chan[mux], &value));
        sum += value;
    }
    return (int16_t)(sum / (int32_t)HALL_SAMPLES_PER_SQUARE);
}

static void scan_board(void) {
    const unsigned per_group = HALL_MUX_CHANNELS / HALL_GROUPS;
    hall_event_t ev;
    bool changed = false;
    for (unsigned group = 0; group < HALL_GROUPS; group++) {
        power_group(group);
        esp_rom_delay_us(HALL_POWER_ON_US);
        for (unsigned channel = group * per_group; channel < (group + 1) * per_group; channel++) {
            select_channel(channel);
            esp_rom_delay_us(HALL_MUX_SETTLE_US);
            for (unsigned mux = 0; mux < HALL_MUX_COUNT; mux++) {
                uint8_t square = SQUARE_OF[mux][channel];
                raw_counts[square] = read_average(mux);
                if (hallscan_update(&scanner, square, raw_counts[square], &ev)) {
                    changed = true;
                }
            }
        }
    }
    if (changed) {
        emit_board();
    }
}

static void setup_gpio(void) {
    gpio_config_t out = {
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    for (int bit = 0; bit < 4; bit++) {
        out.pin_bit_mask |= 1ULL << ADDR_GPIO[bit];
    }
    for (unsigned g = 0; g < HALL_GROUPS; g++) {
        out.pin_bit_mask |= 1ULL << ROW_GPIO[g];
    }
    ESP_ERROR_CHECK(gpio_config(&out));
    power_group(HALL_GROUPS);   /* every row off until the first scan */
}

static void setup_adc(void) {
    adc_oneshot_unit_init_cfg_t unit_cfg = {.unit_id = ADC_UNIT_1};
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit_cfg, &adc));
    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_12,     /* full scale of hall_rfid.esp32.adc_full_scale_mv */
        .bitwidth = ADC_BITWIDTH_12,
    };
    for (unsigned mux = 0; mux < HALL_MUX_COUNT; mux++) {
        adc_unit_t unit;
        ESP_ERROR_CHECK(adc_oneshot_io_to_channel(ADC_GPIO[mux], &unit, &adc_chan[mux]));
        ESP_ERROR_CHECK(adc_oneshot_config_channel(adc, adc_chan[mux], &chan_cfg));
    }
}

static void handle_console(void) {
    uint8_t c;
    while (uart_read_bytes(CONSOLE_PORT, &c, 1, 0) == 1) {
        switch (c) {
        case 'z':
            hallscan_zero(&scanner, raw_counts);
            emit("S,zeroed");
            emit_board();
            break;
        case 'r':
            emit_raw();
            break;
        case 'b':
            emit_board();
            break;
        default:
            break;
        }
    }
}

void app_main(void) {
    uart_config_t ucfg = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_driver_install(CONSOLE_PORT, 1024, 1024, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(CONSOLE_PORT, &ucfg));
    setup_gpio();
    setup_adc();
    hallscan_cfg_t cfg = {
        .on_counts = HALL_ON_COUNTS,
        .off_counts = HALL_OFF_COUNTS,
        .debounce_scans = HALL_DEBOUNCE_SCANS,
        .color_by_polarity = HALL_COLOR_BY_POLARITY,
        .white_positive = HALL_WHITE_POSITIVE,
    };
    hallscan_init(&scanner, &cfg, HALL_BASELINE_COUNTS);
    ESP_LOGI(TAG, "%s, on %d off %d counts, %u groups", HALL_SENSOR, HALL_ON_COUNTS,
             HALL_OFF_COUNTS, (unsigned)HALL_GROUPS);
    uint32_t scans = 0;
    for (;;) {
        scan_board();
        handle_console();
        if (++scans % 1000 == 0) {
            ESP_LOGI(TAG, "%lu scans, %lu changes, %u present", (unsigned long)scans,
                     (unsigned long)scanner.changes,
                     HALL_SQUARES - hallscan_count(&scanner, HALL_EMPTY));
        }
        vTaskDelay(pdMS_TO_TICKS(SCAN_PERIOD_MS));
    }
}
