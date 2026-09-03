/* USART1 (PA9/PA10) is the only serial port of the brain: it goes to the
 * isolated UART shared by the ESP32-S3 module and the Pi header. On the
 * bench a USB-UART adapter on the Pi header gives the CSV console;
 * later the ESP32 relays the same stream. 115200 baud. */

#include "app.h"

#define CONSOLE_BAUD 115200u

void uart_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    gpio_af(MCU_TX_PORT, MCU_TX_PIN, 7u);
    gpio_af(MCU_RX_PORT, MCU_RX_PIN, 7u);
    USART1->BRR = SYSCLK_HZ / CONSOLE_BAUD;
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

void uart_putc(char c) {
    while (!(USART1->ISR & USART_ISR_TXE)) {
    }
    USART1->TDR = (uint8_t)c;
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
    if (USART1->ISR & USART_ISR_RXNE) {
        return (int)(USART1->RDR & 0xFFu);
    }
    return -1;
}
