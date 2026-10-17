/* Hall plus RFID demonstrator (docs/notes/27-demonstrateur-hall-rfid.md)
 * on the ESP32-S3-WROOM-1 of the hallrfid-demo board: two MFRC522 readers
 * on one SPI bus (NSS and NRSTPD per reader), six analog Hall sensors
 * through a CD74HC4067 on ADC1 (two of them also on direct inputs), the
 * switched sensor rail, the field pickup input and the LED. A line
 * console on the native USB (USB-Serial-JTAG) drives the bring-up of
 * measurements/protocol.md: every step of note 25, paragraph 10.1, is a
 * command here. Not compiled in CI (no ESP-IDF toolchain); the driver and
 * the Hall helpers are tested on the host (test/test_hallrfid_demo.c). */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "driver/usb_serial_jtag.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "hall.h"
#include "mfrc522.h"

#define FIRST_CW_GS_P 8u      /* the reduced conductance of a first emission (CWGsP, 0..63) */
#define SPI_HZ 4000000        /* the MFRC522 accepts 10 MHz; 4 MHz leaves margin on the buffer */
#define LINE_LEN 64

static const char *TAG = "hallrfid-demo";
static const char *SITE_NAME[DEMO_SITES] = DEMO_SITE_NAME;
static const unsigned SITE_CHANNEL[DEMO_SITES] = DEMO_SITE_CHANNEL;
static const int SITE_DIRECT_PIN[DEMO_SITES] = DEMO_SITE_DIRECT_PIN;
static const char *READER_NAME[DEMO_READERS] = DEMO_READER_NAME;
static const int READER_NSS[DEMO_READERS] = DEMO_READER_NSS;
static const int READER_NRSTPD[DEMO_READERS] = DEMO_READER_NRSTPD;
static const int ADDR_GPIO[4] = {DEMO_PIN_MUX_S0, DEMO_PIN_MUX_S1, DEMO_PIN_MUX_S2, DEMO_PIN_MUX_S3};
static const uint8_t NXP_VERSION[] = DEMO_NXP_VERSION;

static spi_device_handle_t spi;
static adc_oneshot_unit_handle_t adc;
static adc_channel_t adc_mux, adc_pickup, adc_direct[DEMO_SITES];
static demo_hall_t hall;
static mfrc522_t reader[DEMO_READERS];
static bool rail_on;
static bool led_on;

/* ------------------------------------------------------------ console output */
static void out(const char *s) {
    usb_serial_jtag_write_bytes(s, strlen(s), pdMS_TO_TICKS(100));
}

static void outf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void outf(const char *fmt, ...) {
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    out(buf);
}

/* ------------------------------------------------------------ MFRC522 glue */
static bool spi_xfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    int idx = (int)(intptr_t)ctx;
    spi_transaction_t t = {.length = 8 * n, .tx_buffer = tx, .rx_buffer = rx};
    gpio_set_level(READER_NSS[idx], 0);
    esp_err_t err = spi_device_polling_transmit(spi, &t);
    gpio_set_level(READER_NSS[idx], 1);
    return err == ESP_OK;
}

static void set_nrstpd(void *ctx, bool high) {
    gpio_set_level(READER_NRSTPD[(int)(intptr_t)ctx], high ? 1 : 0);
}

static void delay_ms(void *ctx, unsigned ms) {
    (void)ctx;
    vTaskDelay(pdMS_TO_TICKS(ms ? ms : 1));
}

/* ------------------------------------------------------------ Hall glue */
static void select_channel(unsigned channel) {
    for (int bit = 0; bit < 4; bit++) {
        gpio_set_level(ADDR_GPIO[bit], (channel >> bit) & 1u);
    }
}

static int16_t read_average(adc_channel_t chan) {
    int32_t sum = 0;
    for (unsigned s = 0; s < DEMO_SAMPLES; s++) {
        int value = 0;
        ESP_ERROR_CHECK(adc_oneshot_read(adc, chan, &value));
        sum += value;
    }
    return (int16_t)(sum / (int32_t)DEMO_SAMPLES);
}

static int16_t read_mux(unsigned channel) {
    select_channel(channel);
    esp_rom_delay_us(DEMO_MUX_SETTLE_US);
    return read_average(adc_mux);
}

static void set_rail(bool on) {
    gpio_set_level(DEMO_PIN_ROW_EN1, on ? 0 : 1);   /* P-FET gate, active low */
    rail_on = on;
    if (on) {
        esp_rom_delay_us(DEMO_ROW_ON_US);
    }
}

/* one scan: the reference channels first, then every site through the
 * mux and, where there is one, its direct input. Prints the CSV line
 * H,<site>,<mux counts>,<corrected>,<swing>,<mT>,<pole>,<state>,<direct counts> */
static void scan(bool zero) {
    bool was_on = rail_on;
    if (!was_on) {
        set_rail(true);
    }
    int16_t ground = read_mux(DEMO_CH_GROUND);
    int16_t rail_half = read_mux(DEMO_CH_RAIL_HALF);
    int16_t raw[DEMO_SITES], corrected[DEMO_SITES];
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        raw[i] = read_mux(SITE_CHANNEL[i]);
        corrected[i] = hall_corrected(raw[i], ground, rail_half);
    }
    if (zero) {
        hall_zero(&hall, corrected);
        out("S,zeroed\n");
    }
    outf("REF,ground,%d,rail_half,%d,nominal,%d\n", ground, rail_half, DEMO_RAIL_HALF_COUNTS);
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        int16_t swing = hall_swing(&hall, i, corrected[i]);
        hall_state_t st = hall_update(&hall, i, swing);
        int direct = -1;
        if (SITE_DIRECT_PIN[i] >= 0) {
            direct = read_average(adc_direct[i]);
        }
        outf("H,%s,%d,%d,%d,%.2f,%c,%s,%d\n", SITE_NAME[i], raw[i], corrected[i], swing,
             (double)hall_swing_mt(swing), hall_pole(swing), st == HALL_PRESENT ? "present" : "empty",
             direct);
    }
    if (!was_on) {
        set_rail(false);
    }
}

/* ------------------------------------------------------------ commands */
static void help(void) {
    out("hallrfid-demo console (note 27, section 6)\n"
        "  h            this help\n"
        "  e / E        sensor rail on / off (ROW_EN1)\n"
        "  s            scan the sensors, CSV lines H,...\n"
        "  z            zero: the current readings become the baselines\n"
        "  w <n>        wake reader n (1 = A1, 2 = B1): NRSTPD high, VersionReg, held state\n"
        "  d <n>        reader n hard power-down (NRSTPD low)\n"
        "  v            VersionReg of the readers awake\n"
        "  t <n> <g>    reader n transmits at conductance CWGsP g (0..63)\n"
        "  o <n>        reader n back to the held state (TX1 and TX2 at 0)\n"
        "  r <n>        one read on reader n: UID,<hex>,<sak> or NOTAG\n"
        "  R <n> <k>    k reads on reader n, the count of successes\n"
        "  p            the PICKUP input, counts and millivolts\n"
        "  l            toggle the LED\n"
        "  i            identify: scan, then read the tag of every occupied square\n");
    outf("criteria: idle %.1f mA (max %.0f), TVDD accept %.0f mA on %.0f ohm, "
         "sensor %.0f mA (max %.0f), reads %u (confirm %u)\n",
         DEMO_I_IDLE_MA, DEMO_I_IDLE_MAX_MA, DEMO_I_TVDD_ACCEPT_MA, DEMO_R_SENSE_OHM, DEMO_HALL_I_MA,
         DEMO_HALL_I_MAX_MA, (unsigned)DEMO_READ_TRIALS, (unsigned)DEMO_READ_TRIALS_CONFIRM);
}

static int reader_index(const char *arg) {
    int n = atoi(arg);
    if (n < 1 || n > (int)DEMO_READERS) {
        out("E,reader is 1 or 2\n");
        return -1;
    }
    return n - 1;
}

static void cmd_wake(int idx) {
    mfrc522_status_t st = mfrc522_wake(&reader[idx], FIRST_CW_GS_P);
    bool nxp = false;
    for (unsigned i = 0; i < sizeof NXP_VERSION; i++) {
        nxp = nxp || NXP_VERSION[i] == reader[idx].version;
    }
    outf("W,%s,%s,version,0x%02X,%s,cwgsp,%u\n", READER_NAME[idx], mfrc522_status_name(st),
         reader[idx].version, nxp ? "nxp" : "other", FIRST_CW_GS_P);
}

static void cmd_read(int idx, unsigned trials) {
    unsigned ok = 0;
    char hex[24] = "";
    mfrc522_uid_t uid, last = {0};
    for (unsigned k = 0; k < trials; k++) {
        if (mfrc522_read_uid(&reader[idx], &uid) == MFRC522_OK) {
            ok++;
            last = uid;
        }
        if (trials > 1) {
            vTaskDelay(pdMS_TO_TICKS(20));
        }
    }
    if (trials == 1) {
        if (ok) {
            mfrc522_uid_hex(&last, hex, sizeof hex);
            outf("UID,%s,%s,sak,0x%02X,atqa,%02X%02X\n", READER_NAME[idx], hex, last.sak,
                 last.atqa[1], last.atqa[0]);
        } else {
            outf("NOTAG,%s,%s\n", READER_NAME[idx], mfrc522_status_name(mfrc522_read_uid(&reader[idx], &uid)));
        }
        return;
    }
    mfrc522_uid_hex(&last, hex, sizeof hex);
    outf("READS,%s,%u,%u,uid,%s,cwgsp,%u\n", READER_NAME[idx], ok, trials, hex, reader[idx].cw_gs_p);
}

static void cmd_identify(void) {
    scan(false);
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        if (hall.state[i] != HALL_PRESENT) {
            continue;
        }
        for (unsigned r = 0; r < DEMO_READERS; r++) {
            if (strcmp(READER_NAME[r], SITE_NAME[i]) == 0) {
                bool was = reader[r].transmitting;
                if (!was && mfrc522_transmit(&reader[r]) != MFRC522_OK) {
                    continue;
                }
                cmd_read((int)r, 1);
                if (!was) {
                    mfrc522_hold(&reader[r]);
                }
            }
        }
    }
}

static void handle_line(char *line) {
    char *argv[4] = {0};
    int argc = 0;
    for (char *tok = strtok(line, " \t\r\n"); tok && argc < 4; tok = strtok(NULL, " \t\r\n")) {
        argv[argc++] = tok;
    }
    if (argc == 0) {
        return;
    }
    int idx;
    switch (argv[0][0]) {
    case 'h':
        help();
        break;
    case 'e':
        set_rail(true);
        out("S,rail on\n");
        break;
    case 'E':
        set_rail(false);
        out("S,rail off\n");
        break;
    case 's':
        scan(false);
        break;
    case 'z':
        scan(true);
        break;
    case 'w':
        if (argc >= 2 && (idx = reader_index(argv[1])) >= 0) {
            cmd_wake(idx);
        }
        break;
    case 'd':
        if (argc >= 2 && (idx = reader_index(argv[1])) >= 0) {
            mfrc522_power_down(&reader[idx]);
            outf("S,%s powered down\n", READER_NAME[idx]);
        }
        break;
    case 'v':
        for (unsigned r = 0; r < DEMO_READERS; r++) {
            uint8_t v = 0;
            mfrc522_read(&reader[r], MFRC522_VERSION, &v);
            outf("V,%s,0x%02X\n", READER_NAME[r], v);
        }
        break;
    case 't':
        if (argc >= 3 && (idx = reader_index(argv[1])) >= 0) {
            int g = atoi(argv[2]);
            if (g < 0 || g > (int)MFRC522_CW_GS_P_MAX) {
                out("E,conductance is 0..63\n");
                break;
            }
            mfrc522_status_t st = mfrc522_set_conductance(&reader[idx], (uint8_t)g);
            if (st == MFRC522_OK) {
                st = mfrc522_transmit(&reader[idx]);
            }
            outf("T,%s,%s,cwgsp,%d,read TVDD on TP%u04 vs TP%u05: 1 mV per mA, accept under %.0f mA\n",
                 READER_NAME[idx], mfrc522_status_name(st), g, idx + 1, idx + 1, DEMO_I_TVDD_ACCEPT_MA);
        }
        break;
    case 'o':
        if (argc >= 2 && (idx = reader_index(argv[1])) >= 0) {
            outf("O,%s,%s\n", READER_NAME[idx], mfrc522_status_name(mfrc522_hold(&reader[idx])));
        }
        break;
    case 'r':
        if (argc >= 2 && (idx = reader_index(argv[1])) >= 0) {
            cmd_read(idx, 1);
        }
        break;
    case 'R':
        if (argc >= 3 && (idx = reader_index(argv[1])) >= 0) {
            int k = atoi(argv[2]);
            cmd_read(idx, k > 0 ? (unsigned)k : DEMO_READ_TRIALS);
        }
        break;
    case 'p': {
        int16_t counts = read_average(adc_pickup);
        outf("P,%d,%.1f mV\n", counts, (double)counts * DEMO_ADC_LSB_MV);
        break;
    }
    case 'l':
        led_on = !led_on;
        gpio_set_level(DEMO_PIN_LED, led_on);
        outf("L,%d\n", led_on);
        break;
    case 'i':
        cmd_identify();
        break;
    default:
        out("E,unknown, h for help\n");
        break;
    }
}

/* ------------------------------------------------------------ setup */
static void setup_gpio(void) {
    gpio_config_t cfg = {
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    for (int bit = 0; bit < 4; bit++) {
        cfg.pin_bit_mask |= 1ULL << ADDR_GPIO[bit];
    }
    for (unsigned r = 0; r < DEMO_READERS; r++) {
        cfg.pin_bit_mask |= 1ULL << READER_NSS[r];
        cfg.pin_bit_mask |= 1ULL << READER_NRSTPD[r];
    }
    cfg.pin_bit_mask |= 1ULL << DEMO_PIN_ROW_EN1;
    cfg.pin_bit_mask |= 1ULL << DEMO_PIN_LED;
    ESP_ERROR_CHECK(gpio_config(&cfg));
    for (unsigned r = 0; r < DEMO_READERS; r++) {
        gpio_set_level(READER_NSS[r], 1);       /* not selected */
        gpio_set_level(READER_NRSTPD[r], 0);    /* hard power-down: no emission before a command */
    }
    set_rail(false);
    gpio_set_level(DEMO_PIN_LED, 0);
    gpio_config_t in = {
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,   /* R71 pulls the open-drain IRQ line */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
        .pin_bit_mask = 1ULL << DEMO_PIN_RFID_IRQ,
    };
    ESP_ERROR_CHECK(gpio_config(&in));
}

static void setup_spi(void) {
    spi_bus_config_t bus = {
        .mosi_io_num = DEMO_PIN_SPI_MOSI,
        .miso_io_num = DEMO_PIN_SPI_MISO,
        .sclk_io_num = DEMO_PIN_SPI_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 64,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_DISABLED));
    spi_device_interface_config_t dev = {
        .clock_speed_hz = SPI_HZ,
        .mode = 0,
        .spics_io_num = -1,   /* NSS driven by hand, one line per reader */
        .queue_size = 1,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &dev, &spi));
    for (unsigned r = 0; r < DEMO_READERS; r++) {
        reader[r].io.ctx = (void *)(intptr_t)r;
        reader[r].io.xfer = spi_xfer;
        reader[r].io.set_nrstpd = set_nrstpd;
        reader[r].io.delay_ms = delay_ms;
    }
}

static adc_channel_t adc_of(int gpio) {
    adc_unit_t unit;
    adc_channel_t chan;
    ESP_ERROR_CHECK(adc_oneshot_io_to_channel(gpio, &unit, &chan));
    adc_oneshot_chan_cfg_t cfg = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_12};
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc, chan, &cfg));
    return chan;
}

static void setup_adc(void) {
    adc_oneshot_unit_init_cfg_t unit_cfg = {.unit_id = ADC_UNIT_1};
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit_cfg, &adc));
    adc_mux = adc_of(DEMO_PIN_MUX_OUT);
    adc_pickup = adc_of(DEMO_PIN_PICKUP);
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        if (SITE_DIRECT_PIN[i] >= 0) {
            adc_direct[i] = adc_of(SITE_DIRECT_PIN[i]);
        }
    }
}

void app_main(void) {
    usb_serial_jtag_driver_config_t usb = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    setup_gpio();
    setup_spi();
    setup_adc();
    hall_init(&hall);
    ESP_LOGI(TAG, "%s, on %d off %d counts, %u sites, %u readers", DEMO_SENSOR, DEMO_ON_COUNTS,
             DEMO_OFF_COUNTS, (unsigned)DEMO_SITES, (unsigned)DEMO_READERS);
    out("\nhallrfid-demo ready, readers in hard power-down, sensor rail off; h for help\n");
    char line[LINE_LEN];
    size_t len = 0;
    for (;;) {
        uint8_t c;
        if (usb_serial_jtag_read_bytes(&c, 1, pdMS_TO_TICKS(50)) != 1) {
            continue;
        }
        if (c == '\n' || c == '\r') {
            line[len] = '\0';
            if (len) {
                handle_line(line);
            }
            len = 0;
        } else if (len + 1 < sizeof line) {
            line[len++] = (char)c;
        }
    }
}
