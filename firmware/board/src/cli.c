/* Single-character CLI on the console UART with CSV output.
 *
 * Commands:
 *   h        help
 *   s        one scan of the 64 squares, CSV lines
 *   m / x    start / stop a repeating scan
 *   1..4     scan one quadrant (16 coils)
 *   c        calibration pass: measure all squares, store to flash
 *   i        classify each square against the stored calibration
 *   r        raw ADC dump of quadrant 1 coil 1 (512 samples, CSV)
 *   p / P    drive pulse -100 ns / +100 ns
 *   l        identify and light the squares (demo: even classes white
 *            camp, odd classes black camp; empty square off)
 *   o        all camp LEDs off
 *
 * CSV: q,coil,sq,fa_hz,fb_hz,amp_mv,snr_db10 with sq = file + 8 * rank
 */

#include "app.h"

static bool monitor;
static uint32_t pulse_ns = DRIVE_PULSE_NS;

/* Quadrant-major index to the 8x8 square (file + 8 * rank): quadrants
 * 1 and 3 are the west half, 2 and 4 the east half mounted rotated. */
static uint32_t square_of(uint32_t quadrant, uint32_t coil) {
    uint32_t col = coil % 4u, row = coil / 4u;
    if (quadrant & 1u) {
        col = 3u - col;
        row = 3u - row;
    }
    uint32_t file = (quadrant & 1u) ? 4u + col : col;
    uint32_t rank = (quadrant >= 2u) ? 4u + row : row;
    return file + 8u * rank;
}

static void print_meas(uint32_t sq, measure_t m) {
    uart_put_uint(sq / COILS_PER_QUADRANT + 1u);
    uart_putc(',');
    uart_put_uint(sq % COILS_PER_QUADRANT + 1u);
    uart_putc(',');
    uart_put_uint(square_of(sq / COILS_PER_QUADRANT, sq % COILS_PER_QUADRANT));
    uart_putc(',');
    uart_put_uint(m.fa_hz);
    uart_putc(',');
    uart_put_uint(m.fb_hz);
    uart_putc(',');
    uart_put_uint(m.amp_mv);
    uart_putc(',');
    uart_put_uint(m.snr_db10);
    uart_puts("\n");
}

static void scan_all(void) {
    for (uint32_t sq = 0; sq < N_SQUARES; sq++) {
        print_meas(sq, measure_square(sq));
    }
}

static void do_calibrate(void) {
    calib_t cal = {0};
    uart_puts("# calibration: place the test pieces, measuring...\n");
    for (uint32_t sq = 0; sq < N_SQUARES; sq++) {
        uint64_t acc = 0u;
        for (uint32_t k = 0; k < 16u; k++) {
            acc += measure_square(sq).fa_hz;
        }
        cal.freq_hz[sq] = (uint32_t)(acc / 16u);
    }
    if (calib_store(&cal)) {
        uart_puts("# stored:");
        for (uint32_t sq = 0; sq < N_SQUARES; sq++) {
            uart_putc(' ');
            uart_put_uint(cal.freq_hz[sq]);
        }
        uart_puts("\n");
    } else {
        uart_puts("# flash store FAILED\n");
    }
}

static void do_light(void) {
    calib_t cal;
    if (!calib_load(&cal)) {
        uart_puts("# no calibration stored\n");
        return;
    }
    for (uint32_t sq = 0; sq < N_SQUARES; sq++) {
        measure_t m = measure_square(sq);
        int cls = calib_classify(&cal, m.fa_hz);
        led_camp_t camp = LED_CAMP_OFF;
        if (cls >= 0) {
            camp = (cls % 2 == 0) ? LED_CAMP_WHITE : LED_CAMP_BLACK;
        }
        led_set_square(square_of(sq / COILS_PER_QUADRANT, sq % COILS_PER_QUADRANT), camp);
    }
    led_apply();
    uart_puts("# leds updated\n");
}

static void do_identify(void) {
    calib_t cal;
    if (!calib_load(&cal)) {
        uart_puts("# no calibration stored\n");
        return;
    }
    for (uint32_t sq = 0; sq < N_SQUARES; sq++) {
        measure_t m = measure_square(sq);
        int cls = calib_classify(&cal, m.fa_hz);
        uart_puts("# sq ");
        uart_put_uint(sq + 1u);
        uart_puts(": f=");
        uart_put_uint(m.fa_hz);
        uart_puts(" -> class ");
        uart_put_int(cls + 1);
        uart_puts("\n");
    }
}

static void dump_raw(void) {
    measure_square(0u);
    uart_puts("# raw q1 coil1, fs_hz=");
    uart_put_uint(adc_sample_rate_hz());
    uart_puts("\n");
    for (uint32_t i = 0; i < ADC_SAMPLES; i++) {
        uart_put_uint(adc_buf[i]);
        uart_puts("\n");
    }
}

void cli_poll(void) {
    int c = uart_getc_nonblock();
    if (c < 0) {
        if (monitor) {
            scan_all();
            delay_ms(200u);
        }
        return;
    }
    switch (c) {
    case 'h':
        uart_puts("# s scan | m/x monitor | 1..4 quadrant | c calibrate | "
                  "i identify | r raw | p/P pulse\n");
        break;
    case 's':
        scan_all();
        break;
    case 'm':
        monitor = true;
        break;
    case 'x':
        monitor = false;
        break;
    case '1':
    case '2':
    case '3':
    case '4':
        for (uint32_t k = 0; k < COILS_PER_QUADRANT; k++) {
            uint32_t sq = (uint32_t)(c - '1') * COILS_PER_QUADRANT + k;
            print_meas(sq, measure_square(sq));
        }
        break;
    case 'c':
        do_calibrate();
        break;
    case 'i':
        do_identify();
        break;
    case 'r':
        dump_raw();
        break;
    case 'l':
        do_light();
        break;
    case 'o':
        led_all_off();
        uart_puts("# leds off\n");
        break;
    case 'p':
        if (pulse_ns > 200u) {
            pulse_ns -= 100u;
        }
        measure_set_drive_pulse_ns(pulse_ns);
        uart_puts("# pulse_ns=");
        uart_put_uint(pulse_ns);
        uart_puts("\n");
        break;
    case 'P':
        pulse_ns += 100u;
        measure_set_drive_pulse_ns(pulse_ns);
        uart_puts("# pulse_ns=");
        uart_put_uint(pulse_ns);
        uart_puts("\n");
        break;
    default:
        break;
    }
}
