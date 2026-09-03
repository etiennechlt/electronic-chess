/* Nordic UART Service over NimBLE: the bridge is the peripheral, the
 * clock (or a phone) the central. Both sides exchange whole lines. */
#ifndef NUS_H
#define NUS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define NUS_NAME_PREFIX "echecs-"
#define PROTO_LINE_MAX_BLE 244   /* one line per notification, MTU 247 */

typedef void (*nus_rx_cb_t)(const uint8_t *data, size_t n, void *ctx);

/* Peripheral side (bridge): advertises "echecs-XXXX", accepts one central. */
void nus_peripheral_start(nus_rx_cb_t on_rx, void *ctx);
bool nus_peripheral_send(const char *line);
bool nus_peripheral_connected(void);

/* Central side (clock): scans for the prefix, connects, subscribes. */
void nus_central_start(nus_rx_cb_t on_rx, void *ctx);
bool nus_central_send(const char *line);
bool nus_central_connected(void);

#endif
