/* Nordic UART Service on NimBLE (ESP-IDF 5.x). Written against the
 * NimBLE host API; not compiled in this repository's CI (no ESP-IDF
 * toolchain there), see firmware/esp32/README.md. */
#include "nus.h"

#include <string.h>

#include "esp_log.h"
#include "esp_mac.h"
#include "host/ble_gap.h"
#include "host/ble_gatt.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "nus";

static const ble_uuid128_t UUID_SVC =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0, 0x93, 0xf3, 0xa3, 0xb5, 0x01,
                     0x00, 0x40, 0x6e);
static const ble_uuid128_t UUID_RX =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0, 0x93, 0xf3, 0xa3, 0xb5, 0x02,
                     0x00, 0x40, 0x6e);
static const ble_uuid128_t UUID_TX =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0, 0x93, 0xf3, 0xa3, 0xb5, 0x03,
                     0x00, 0x40, 0x6e);

static nus_rx_cb_t rx_cb;
static void *rx_ctx;
static uint16_t conn_handle = BLE_HS_CONN_HANDLE_NONE;
static uint16_t tx_val_handle;       /* peripheral: our TX characteristic */
static uint16_t peer_rx_handle;      /* central: the peer's RX characteristic */
static uint16_t peer_tx_handle;      /* central: the peer's TX characteristic */
static bool is_central;
static char dev_name[16];

static void make_name(void) {
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_BT);
    snprintf(dev_name, sizeof dev_name, NUS_NAME_PREFIX "%02x%02x", mac[4], mac[5]);
}

/* ---------------------------------------------------------------- peripheral */

static int rx_write_cb(uint16_t ch, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    (void)ch; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR && rx_cb) {
        uint8_t buf[PROTO_LINE_MAX_BLE];
        uint16_t n = OS_MBUF_PKTLEN(ctxt->om);
        if (n > sizeof buf) {
            n = sizeof buf;
        }
        ble_hs_mbuf_to_flat(ctxt->om, buf, n, NULL);
        rx_cb(buf, n, rx_ctx);
    }
    return 0;
}

static int tx_access_cb(uint16_t ch, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    (void)ch; (void)attr; (void)ctxt; (void)arg;
    return 0;                          /* notify only */
}

static const struct ble_gatt_svc_def gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &UUID_SVC.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            {.uuid = &UUID_RX.u, .access_cb = rx_write_cb,
             .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP},
            {.uuid = &UUID_TX.u, .access_cb = tx_access_cb, .val_handle = &tx_val_handle,
             .flags = BLE_GATT_CHR_F_NOTIFY},
            {0},
        },
    },
    {0},
};

static void advertise(void);

static int gap_event_peripheral(struct ble_gap_event *ev, void *arg) {
    (void)arg;
    switch (ev->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (ev->connect.status == 0) {
            conn_handle = ev->connect.conn_handle;
            ble_gattc_exchange_mtu(conn_handle, NULL, NULL);
            ESP_LOGI(TAG, "central connected");
        } else {
            advertise();
        }
        return 0;
    case BLE_GAP_EVENT_DISCONNECT:
        conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "central disconnected, advertising again");
        advertise();
        return 0;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        advertise();
        return 0;
    default:
        return 0;
    }
}

static void advertise(void) {
    struct ble_hs_adv_fields fields = {0};
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (uint8_t *)dev_name;
    fields.name_len = strlen(dev_name);
    fields.name_is_complete = 1;
    fields.uuids128 = (ble_uuid128_t *)&UUID_SVC;
    fields.num_uuids128 = 1;
    fields.uuids128_is_complete = 1;
    ble_gap_adv_set_fields(&fields);
    struct ble_gap_adv_params params = {0};
    params.conn_mode = BLE_GAP_CONN_MODE_UND;
    params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &params, gap_event_peripheral,
                      NULL);
}

static void on_sync_peripheral(void) {
    ble_hs_util_ensure_addr(0);
    advertise();
}

static void host_task(void *arg) {
    (void)arg;
    nimble_port_run();
    nimble_port_freertos_deinit();
}

void nus_peripheral_start(nus_rx_cb_t on_rx, void *ctx) {
    rx_cb = on_rx;
    rx_ctx = ctx;
    is_central = false;
    make_name();
    nimble_port_init();
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(gatt_svcs);
    ble_gatts_add_svcs(gatt_svcs);
    ble_svc_gap_device_name_set(dev_name);
    ble_hs_cfg.sync_cb = on_sync_peripheral;
    ble_att_set_preferred_mtu(247);
    nimble_port_freertos_init(host_task);
}

bool nus_peripheral_send(const char *line) {
    if (conn_handle == BLE_HS_CONN_HANDLE_NONE) {
        return false;
    }
    struct os_mbuf *om = ble_hs_mbuf_from_flat(line, strlen(line));
    return om && ble_gatts_notify_custom(conn_handle, tx_val_handle, om) == 0;
}

bool nus_peripheral_connected(void) {
    return conn_handle != BLE_HS_CONN_HANDLE_NONE;
}

/* ------------------------------------------------------------------- central */

static void scan(void);

static int on_subscribe(uint16_t ch, const struct ble_gatt_error *err,
                        struct ble_gatt_attr *attr, void *arg) {
    (void)ch; (void)attr; (void)arg;
    ESP_LOGI(TAG, "subscribed to TX, status %d", err->status);
    return 0;
}

static int on_chr(uint16_t ch, const struct ble_gatt_error *err,
                  const struct ble_gatt_chr *chr, void *arg) {
    (void)arg;
    if (err->status == 0 && chr) {
        if (ble_uuid_cmp(&chr->uuid.u, &UUID_RX.u) == 0) {
            peer_rx_handle = chr->val_handle;
        } else if (ble_uuid_cmp(&chr->uuid.u, &UUID_TX.u) == 0) {
            peer_tx_handle = chr->val_handle;
        }
    } else if (err->status == BLE_HS_EDONE && peer_tx_handle) {
        /* enable notifications: write 0x0001 to the CCCD that follows TX */
        uint8_t v[2] = {1, 0};
        ble_gattc_write_flat(ch, peer_tx_handle + 1, v, sizeof v, on_subscribe, NULL);
    }
    return 0;
}

static int on_svc(uint16_t ch, const struct ble_gatt_error *err,
                  const struct ble_gatt_svc *svc, void *arg) {
    (void)arg;
    if (err->status == 0 && svc) {
        ble_gattc_disc_all_chrs(ch, svc->start_handle, svc->end_handle, on_chr, NULL);
    }
    return 0;
}

static int gap_event_central(struct ble_gap_event *ev, void *arg) {
    (void)arg;
    switch (ev->type) {
    case BLE_GAP_EVENT_DISC: {
        struct ble_hs_adv_fields f;
        if (ble_hs_adv_parse_fields(&f, ev->disc.data, ev->disc.length_data) != 0) {
            return 0;
        }
        if (f.name_len >= strlen(NUS_NAME_PREFIX) &&
            memcmp(f.name, NUS_NAME_PREFIX, strlen(NUS_NAME_PREFIX)) == 0) {
            ble_gap_disc_cancel();
            ble_gap_connect(BLE_OWN_ADDR_PUBLIC, &ev->disc.addr, 10000, NULL, gap_event_central,
                            NULL);
        }
        return 0;
    }
    case BLE_GAP_EVENT_CONNECT:
        if (ev->connect.status == 0) {
            conn_handle = ev->connect.conn_handle;
            ble_gattc_exchange_mtu(conn_handle, NULL, NULL);
            ble_gattc_disc_svc_by_uuid(conn_handle, &UUID_SVC.u, on_svc, NULL);
            ESP_LOGI(TAG, "connected to the board");
        } else {
            scan();
        }
        return 0;
    case BLE_GAP_EVENT_DISCONNECT:
        conn_handle = BLE_HS_CONN_HANDLE_NONE;
        peer_rx_handle = peer_tx_handle = 0;
        scan();
        return 0;
    case BLE_GAP_EVENT_NOTIFY_RX:
        if (rx_cb) {
            uint8_t buf[PROTO_LINE_MAX_BLE];
            uint16_t n = OS_MBUF_PKTLEN(ev->notify_rx.om);
            if (n > sizeof buf) {
                n = sizeof buf;
            }
            ble_hs_mbuf_to_flat(ev->notify_rx.om, buf, n, NULL);
            rx_cb(buf, n, rx_ctx);
        }
        return 0;
    case BLE_GAP_EVENT_DISC_COMPLETE:
        if (conn_handle == BLE_HS_CONN_HANDLE_NONE) {
            scan();
        }
        return 0;
    default:
        return 0;
    }
}

static void scan(void) {
    struct ble_gap_disc_params p = {0};
    p.passive = 1;
    p.filter_duplicates = 1;
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 5000, &p, gap_event_central, NULL);
}

static void on_sync_central(void) {
    ble_hs_util_ensure_addr(0);
    scan();
}

void nus_central_start(nus_rx_cb_t on_rx, void *ctx) {
    rx_cb = on_rx;
    rx_ctx = ctx;
    is_central = true;
    make_name();
    nimble_port_init();
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_svc_gap_device_name_set("horloge");
    ble_hs_cfg.sync_cb = on_sync_central;
    ble_att_set_preferred_mtu(247);
    nimble_port_freertos_init(host_task);
}

bool nus_central_send(const char *line) {
    if (conn_handle == BLE_HS_CONN_HANDLE_NONE || !peer_rx_handle) {
        return false;
    }
    return ble_gattc_write_no_rsp_flat(conn_handle, peer_rx_handle, line, strlen(line)) == 0;
}

bool nus_central_connected(void) {
    return conn_handle != BLE_HS_CONN_HANDLE_NONE && peer_rx_handle != 0;
}
