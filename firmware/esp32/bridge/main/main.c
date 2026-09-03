/* Radio bridge on the brain: relays the STM32 console lines (UART1,
 * through the ADuM1201) to a BLE Nordic UART Service and back. The STM32
 * stays the master of the game; this firmware never interprets the
 * lines except to count them. WiFi and the Lichess client come later.
 *
 * Not compiled in CI (no ESP-IDF toolchain), see ../README.md. */
#include <string.h>

#include "driver/uart.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nus.h"
#include "proto.h"

#define UART_PORT UART_NUM_1
#define UART_TX_PIN 17               /* TXD0 of the module is the console; the */
#define UART_RX_PIN 18               /* board link uses UART1 on free pins */
#define UART_BAUD 115200

static const char *TAG = "bridge";
static proto_reader_t from_board;
static proto_reader_t from_ble;
static uint32_t lines_up, lines_down;

/* board -> BLE */
static void on_board_line(const char *line, void *ctx) {
    (void)ctx;
    char out[PROTO_LINE_MAX + 1];
    snprintf(out, sizeof out, "%s\n", line);
    if (nus_peripheral_send(out)) {
        lines_up++;
    }
}

/* BLE -> board */
static void on_ble_line(const char *line, void *ctx) {
    (void)ctx;
    proto_msg_t m;
    if (!proto_parse(line, &m)) {
        from_ble.dropped++;
        return;
    }
    uart_write_bytes(UART_PORT, line, strlen(line));
    uart_write_bytes(UART_PORT, "\n", 1);
    lines_down++;
}

static void on_ble_rx(const uint8_t *data, size_t n, void *ctx) {
    proto_reader_feed(&from_ble, data, n, on_ble_line, ctx);
    if (n > 0 && data[n - 1] != '\n') {
        proto_reader_feed(&from_ble, (const uint8_t *)"\n", 1, on_ble_line, ctx);
    }
}

static void uart_task(void *arg) {
    (void)arg;
    uint8_t buf[128];
    for (;;) {
        int n = uart_read_bytes(UART_PORT, buf, sizeof buf, pdMS_TO_TICKS(20));
        if (n > 0) {
            proto_reader_feed(&from_board, buf, (size_t)n, on_board_line, NULL);
        }
    }
}

void app_main(void) {
    uart_config_t cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_driver_install(UART_PORT, 1024, 1024, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_PORT, &cfg));
    ESP_ERROR_CHECK(uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE,
                                 UART_PIN_NO_CHANGE));
    nus_peripheral_start(on_ble_rx, NULL);
    xTaskCreate(uart_task, "uart", 4096, NULL, 10, NULL);
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(10000));
        ESP_LOGI(TAG, "ble %s, up %lu, down %lu, dropped %lu/%lu",
                 nus_peripheral_connected() ? "connected" : "idle", (unsigned long)lines_up,
                 (unsigned long)lines_down, (unsigned long)from_board.dropped,
                 (unsigned long)from_ble.dropped);
    }
}
