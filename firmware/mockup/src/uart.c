/* USART2 (PA2/PA3, ST-Link VCP) for CSV and CLI at 921600 baud;
 * USART1 (PA9/PA10) for the isolated Pi link at 115200 baud. */

#include "app.h"

#define VCP_BAUD 921600u
#define PI_BAUD 115200u

void uart_init(void) {
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_USART2EN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    gpio_af(GPIOA, 2u, 7u);   /* USART2_TX */
    gpio_af(GPIOA, 3u, 7u);   /* USART2_RX */
    gpio_af(GPIOA, 9u, 7u);   /* USART1_TX -> isolator -> Pi RXD */
    gpio_af(GPIOA, 10u, 7u);  /* USART1_RX <- isolator <- Pi TXD */

    USART2->BRR = SYSCLK_HZ / VCP_BAUD;
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
    USART1->BRR = SYSCLK_HZ / PI_BAUD;
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

void uart_putc(char c) {
    while (!(USART2->ISR & USART_ISR_TXE)) {
    }
    USART2->TDR = (uint8_t)c;
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
    if (USART2->ISR & USART_ISR_RXNE) {
        return (int)(USART2->RDR & 0xFFu);
    }
    return -1;
}

void pi_uart_putc(char c) {
    while (!(USART1->ISR & USART_ISR_TXE)) {
    }
    USART1->TDR = (uint8_t)c;
}

int pi_uart_getc_nonblock(void) {
    if (USART1->ISR & USART_ISR_RXNE) {
        return (int)(USART1->RDR & 0xFFu);
    }
    return -1;
}
