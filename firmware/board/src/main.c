/* Brain board firmware entry (ADR 0010): scans the four quadrants over
 * the shared coil bus, reports fa (FFT) on every coil and fb (comparator)
 * on quadrant 1, drives the 128 camp LEDs. Console on USART1, or on the
 * ST-Link virtual COM port when built with NUCLEO=1 (one reduced
 * quadrant of four coils on a Nucleo-G474RE, note 19). */

#include "app.h"

int main(void) {
    clock_init_170mhz();
    dwt_init();
    uart_init();
    adc_init();
    comp_init();
    fft_init();
    measure_init();
    led_init();

    uart_puts("# LC chessboard, " BOARD_NAME ", ");
    uart_put_uint(N_QUADRANTS);
    uart_puts(" quadrant(s) x ");
    uart_put_uint(COILS_PER_QUADRANT);
    uart_puts(" coils\n");
    uart_puts("# fs_hz=");
    uart_put_uint(adc_sample_rate_hz());
    uart_puts(" band=200k..650k, h for help\n");
    uart_puts("# csv: q,coil,sq,fa_hz,fb_hz,amp_mv,snr_db10\n");

    for (;;) {
        cli_poll();
    }
}
