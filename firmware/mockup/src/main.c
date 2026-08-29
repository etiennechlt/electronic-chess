/* Mockup firmware entry: both frequency-extraction paths live side by
 * side (brief 5.2); every scan reports fa (FFT) and fb (comparator)
 * so the notebook can compare them on the same ringdowns. */

#include "app.h"

int main(void) {
    clock_init_170mhz();
    dwt_init();
    uart_init();
    adc_init();
    comp_init();
    fft_init();
    measure_init();

    uart_puts("# LC chessboard, 2x2 mockup\n");
    uart_puts("# fs_hz=");
    uart_put_uint(adc_sample_rate_hz());
    uart_puts(" band=200k..650k, h for help\n");
    uart_puts("# csv: sq,fa_hz,fb_hz,amp_mv,snr_db10\n");

    for (;;) {
        cli_poll();
    }
}
