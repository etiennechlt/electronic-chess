/* Console. On the brain, USART1 (PA9/PA10) is the only serial port: it
 * goes to the isolated UART shared by the ESP32-S3 module and the Pi
 * header; a USB-UART adapter on the Pi header gives the CSV console,
 * later the ESP32 relays the same stream. With NUCLEO=1 the console is
 * USART2 on the pins of the ST-Link virtual COM port (bench.console in
 * config/board.yaml). 115200 baud, APB1 and APB2 both at SYSCLK. */

#include "app.h"

#define CONSOLE_BAUD 115200u

void uart_init(void) {
    gpio_clock_enable(CONSOLE_TX_PORT);
    gpio_clock_enable(CONSOLE_RX_PORT);
    CONSOLE_CLK_ENABLE();
    gpio_af(CONSOLE_TX_PORT, CONSOLE_TX_PIN, 7u);
    gpio_af(CONSOLE_RX_PORT, CONSOLE_RX_PIN, 7u);
    CONSOLE_USART->BRR = SYSCLK_HZ / CONSOLE_BAUD;
    CONSOLE_USART->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

void uart_putc(char c) {
    while (!(CONSOLE_USART->ISR & USART_ISR_TXE)) {
    }
    CONSOLE_USART->TDR = (uint8_t)c;
}

void uart_puts(const char *s) {
    while (*s) {
        if (*s == '\n') {
            uart_putc('\r');
        }
        uart_putc(*s++);
    }
}

void uart_put_uint(uint32_t v) {
    char buf[11];
    int i = 10;
    buf[i] = '\0';
    do {
        buf[--i] = (char)('0' + (v % 10u));
        v /= 10u;
    } while (v && i > 0);
    uart_puts(&buf[i]);
}

void uart_put_int(int32_t v) {
    if (v < 0) {
        uart_putc('-');
        v = -v;
    }
    uart_put_uint((uint32_t)v);
}

int uart_getc_nonblock(void) {
    if (CONSOLE_USART->ISR & USART_ISR_RXNE) {
        return (int)(CONSOLE_USART->RDR & 0xFFu);
    }
    return -1;
}
