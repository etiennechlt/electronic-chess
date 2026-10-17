/* MFRC522 register logic and ISO 14443A read sequence, hardware behind
 * mfrc522_io_t (see mfrc522.h). The SPI address byte is the datasheet's:
 * bit 7 read, bits 6 to 1 the address, bit 0 zero. */
#include "mfrc522.h"

#include <stdio.h>
#include <string.h>

#define TRANSCEIVE_POLLS 40u   /* 40 polls of 1 ms over the chip's 25 ms timer */

static bool spi2(mfrc522_t *d, uint8_t a, uint8_t b, uint8_t rx[2]) {
    uint8_t tx[2] = {a, b};
    return d->io.xfer(d->io.ctx, tx, rx, 2);
}

bool mfrc522_read(mfrc522_t *d, uint8_t reg, uint8_t *value) {
    uint8_t rx[2];
    if (!spi2(d, (uint8_t)(0x80u | ((reg << 1) & 0x7Eu)), 0x00, rx)) {
        return false;
    }
    *value = rx[1];
    return true;
}

bool mfrc522_write(mfrc522_t *d, uint8_t reg, uint8_t value) {
    uint8_t rx[2];
    return spi2(d, (uint8_t)((reg << 1) & 0x7Eu), value, rx);
}

bool mfrc522_set_bits(mfrc522_t *d, uint8_t reg, uint8_t mask) {
    uint8_t v;
    return mfrc522_read(d, reg, &v) && mfrc522_write(d, reg, (uint8_t)(v | mask));
}

bool mfrc522_clear_bits(mfrc522_t *d, uint8_t reg, uint8_t mask) {
    uint8_t v;
    return mfrc522_read(d, reg, &v) && mfrc522_write(d, reg, (uint8_t)(v & (uint8_t)~mask));
}

#define W(reg, val)                                   \
    do {                                              \
        if (!mfrc522_write(d, (reg), (val))) {        \
            return MFRC522_IO;                        \
        }                                             \
    } while (0)

mfrc522_status_t mfrc522_set_conductance(mfrc522_t *d, uint8_t cw_gs_p) {
    if (cw_gs_p > MFRC522_CW_GS_P_MAX) {
        cw_gs_p = MFRC522_CW_GS_P_MAX;
    }
    uint8_t gsn;
    if (!mfrc522_read(d, MFRC522_GS_N, &gsn)) {
        return MFRC522_IO;
    }
    W(MFRC522_CW_GS_P, cw_gs_p);
    /* CWGsN is the upper nibble (0..15): in proportion to CWGsP */
    W(MFRC522_GS_N, (uint8_t)((gsn & 0x0Fu) | (uint8_t)((cw_gs_p >> 2) << 4)));
    d->cw_gs_p = cw_gs_p;
    return MFRC522_OK;
}

mfrc522_status_t mfrc522_hold(mfrc522_t *d) {
    W(MFRC522_TX_ASK, MFRC522_FORCE_100_ASK);
    W(MFRC522_TX_SEL, MFRC522_DRIVER_SEL_MFIN | MFRC522_MFOUT_SEL_3STATE);
    W(MFRC522_TX_CONTROL, MFRC522_TX1_RF_EN | MFRC522_TX2_RF_EN);
    d->transmitting = false;
    return MFRC522_OK;
}

mfrc522_status_t mfrc522_transmit(mfrc522_t *d) {
    W(MFRC522_TX_ASK, MFRC522_FORCE_100_ASK);
    W(MFRC522_TX_SEL, MFRC522_DRIVER_SEL_ENCODER | MFRC522_MFOUT_SEL_3STATE);
    W(MFRC522_TX_CONTROL, MFRC522_TX1_RF_EN | MFRC522_TX2_RF_EN);
    d->transmitting = true;
    return MFRC522_OK;
}

mfrc522_status_t mfrc522_wake(mfrc522_t *d, uint8_t cw_gs_p) {
    d->io.set_nrstpd(d->io.ctx, true);
    d->io.delay_ms(d->io.ctx, 2);
    W(MFRC522_COMMAND, MFRC522_CMD_SOFT_RESET);
    d->io.delay_ms(d->io.ctx, 50);   /* the oscillator start-up, with margin */
    /* timer: TAuto, prescaler 169 and reload 1000: 25 ms */
    W(MFRC522_T_MODE, 0x80);
    W(MFRC522_T_PRESCALER, 0xA9);
    W(MFRC522_T_RELOAD_H, 0x03);
    W(MFRC522_T_RELOAD_L, 0xE8);
    W(MFRC522_MODE, 0x3D);        /* CRC preset 6363h, TxWaitRF, MFIN polarity */
    W(MFRC522_TX_MODE, 0x00);     /* 106 kbit/s, CRC handled by the driver */
    W(MFRC522_RX_MODE, 0x00);
    W(MFRC522_MOD_WIDTH, 0x26);
    mfrc522_status_t st = mfrc522_set_conductance(d, cw_gs_p);
    if (st != MFRC522_OK) {
        return st;
    }
    if (!mfrc522_read(d, MFRC522_VERSION, &d->version)) {
        return MFRC522_IO;
    }
    return mfrc522_hold(d);
}

void mfrc522_power_down(mfrc522_t *d) {
    d->io.set_nrstpd(d->io.ctx, false);
    d->transmitting = false;
}

static bool fifo_write(mfrc522_t *d, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (!mfrc522_write(d, MFRC522_FIFO_DATA, data[i])) {
            return false;
        }
    }
    return true;
}

mfrc522_status_t mfrc522_crc(mfrc522_t *d, const uint8_t *data, size_t len, uint8_t out[2]) {
    W(MFRC522_COMMAND, MFRC522_CMD_IDLE);
    W(MFRC522_DIV_IRQ, MFRC522_DIV_IRQ_CRC);   /* clear */
    W(MFRC522_FIFO_LEVEL, 0x80);                /* flush */
    if (!fifo_write(d, data, len)) {
        return MFRC522_IO;
    }
    W(MFRC522_COMMAND, MFRC522_CMD_CALC_CRC);
    for (unsigned i = 0; i < 100; i++) {
        uint8_t irq;
        if (!mfrc522_read(d, MFRC522_DIV_IRQ, &irq)) {
            return MFRC522_IO;
        }
        if (irq & MFRC522_DIV_IRQ_CRC) {
            W(MFRC522_COMMAND, MFRC522_CMD_IDLE);
            if (!mfrc522_read(d, MFRC522_CRC_RESULT_L, &out[0]) ||
                !mfrc522_read(d, MFRC522_CRC_RESULT_H, &out[1])) {
                return MFRC522_IO;
            }
            return MFRC522_OK;
        }
    }
    return MFRC522_TIMEOUT;
}

mfrc522_status_t mfrc522_transceive(mfrc522_t *d, const uint8_t *tx, size_t tx_len, uint8_t tx_bits,
                                    uint8_t *rx, size_t *rx_len) {
    W(MFRC522_COMMAND, MFRC522_CMD_IDLE);
    W(MFRC522_COM_IRQ, 0x7F);        /* clear every request */
    W(MFRC522_FIFO_LEVEL, 0x80);     /* flush */
    if (!fifo_write(d, tx, tx_len)) {
        return MFRC522_IO;
    }
    W(MFRC522_BIT_FRAMING, (uint8_t)(tx_bits & 0x07u));
    W(MFRC522_COMMAND, MFRC522_CMD_TRANSCEIVE);
    if (!mfrc522_set_bits(d, MFRC522_BIT_FRAMING, 0x80)) {   /* StartSend */
        return MFRC522_IO;
    }
    uint8_t irq = 0;
    bool done = false;
    for (unsigned i = 0; i < TRANSCEIVE_POLLS && !done; i++) {
        if (!mfrc522_read(d, MFRC522_COM_IRQ, &irq)) {
            return MFRC522_IO;
        }
        if (irq & (MFRC522_IRQ_RX | MFRC522_IRQ_IDLE)) {
            done = true;
        } else if (irq & MFRC522_IRQ_TIMER) {
            break;
        } else {
            d->io.delay_ms(d->io.ctx, 1);
        }
    }
    if (!mfrc522_clear_bits(d, MFRC522_BIT_FRAMING, 0x80)) {
        return MFRC522_IO;
    }
    if (!done) {
        return MFRC522_TIMEOUT;
    }
    uint8_t err;
    if (!mfrc522_read(d, MFRC522_ERROR_REG, &err)) {
        return MFRC522_IO;
    }
    if (err & (MFRC522_ERR_BUFFER_OVFL | MFRC522_ERR_PARITY | MFRC522_ERR_PROTOCOL)) {
        return MFRC522_ERROR;
    }
    if (err & MFRC522_ERR_COLL) {
        return MFRC522_COLLISION;
    }
    uint8_t level;
    if (!mfrc522_read(d, MFRC522_FIFO_LEVEL, &level)) {
        return MFRC522_IO;
    }
    if (level > *rx_len) {
        return MFRC522_ERROR;
    }
    for (uint8_t i = 0; i < level; i++) {
        if (!mfrc522_read(d, MFRC522_FIFO_DATA, &rx[i])) {
            return MFRC522_IO;
        }
    }
    *rx_len = level;
    return MFRC522_OK;
}

uint16_t mfrc522_crc_a(const uint8_t *data, size_t len) {
    uint16_t crc = 0x6363;
    for (size_t i = 0; i < len; i++) {
        uint8_t b = (uint8_t)(data[i] ^ (crc & 0xFFu));
        b = (uint8_t)(b ^ (uint8_t)(b << 4));
        crc = (uint16_t)((crc >> 8) ^ ((uint16_t)b << 8) ^ ((uint16_t)b << 3) ^ ((uint16_t)b >> 4));
    }
    return crc;
}

mfrc522_status_t mfrc522_read_uid(mfrc522_t *d, mfrc522_uid_t *uid) {
    memset(uid, 0, sizeof *uid);
    /* REQA: a 7-bit frame */
    uint8_t reqa = 0x26;
    size_t n = 2;
    mfrc522_status_t st = mfrc522_transceive(d, &reqa, 1, 7, uid->atqa, &n);
    if (st != MFRC522_OK) {
        return st;
    }
    if (n != 2) {
        return MFRC522_ERROR;
    }
    static const uint8_t SEL[3] = {0x93, 0x95, 0x97};
    for (unsigned level = 0; level < 3; level++) {
        /* anticollision: SEL, NVB 0x20; the tag answers 4 bytes and their BCC */
        uint8_t cmd[9] = {SEL[level], 0x20};
        uint8_t ans[5];
        n = sizeof ans;
        st = mfrc522_transceive(d, cmd, 2, 0, ans, &n);
        if (st != MFRC522_OK) {
            return st;
        }
        if (n != 5 || (uint8_t)(ans[0] ^ ans[1] ^ ans[2] ^ ans[3]) != ans[4]) {
            return MFRC522_BAD_CRC;
        }
        /* SELECT: SEL, NVB 0x70, the 4 bytes, BCC, CRC_A; the tag answers SAK and CRC_A */
        cmd[1] = 0x70;
        memcpy(&cmd[2], ans, 5);
        if ((st = mfrc522_crc(d, cmd, 7, &cmd[7])) != MFRC522_OK) {
            return st;
        }
        uint8_t sak[3];
        n = sizeof sak;
        st = mfrc522_transceive(d, cmd, 9, 0, sak, &n);
        if (st != MFRC522_OK) {
            return st;
        }
        if (n != 3) {
            return MFRC522_ERROR;
        }
        uint8_t crc[2];
        if ((st = mfrc522_crc(d, sak, 1, crc)) != MFRC522_OK) {
            return st;
        }
        if (crc[0] != sak[1] || crc[1] != sak[2]) {
            return MFRC522_BAD_CRC;
        }
        uid->sak = sak[0];
        if (sak[0] & 0x04) {
            /* cascade bit: the first byte was the cascade tag 0x88, three UID bytes follow */
            if (ans[0] != 0x88 || level == 2) {
                return MFRC522_ERROR;
            }
            memcpy(&uid->uid[uid->len], &ans[1], 3);
            uid->len = (uint8_t)(uid->len + 3);
        } else {
            memcpy(&uid->uid[uid->len], ans, 4);
            uid->len = (uint8_t)(uid->len + 4);
            return MFRC522_OK;
        }
    }
    return MFRC522_ERROR;
}

const char *mfrc522_status_name(mfrc522_status_t s) {
    switch (s) {
    case MFRC522_OK:
        return "ok";
    case MFRC522_TIMEOUT:
        return "notag";
    case MFRC522_COLLISION:
        return "collision";
    case MFRC522_ERROR:
        return "error";
    case MFRC522_BAD_CRC:
        return "badcrc";
    case MFRC522_IO:
        return "io";
    }
    return "?";
}

void mfrc522_uid_hex(const mfrc522_uid_t *uid, char *out, size_t out_len) {
    size_t pos = 0;
    out[0] = '\0';
    for (unsigned i = 0; i < uid->len && pos + 3 <= out_len; i++) {
        pos += (size_t)snprintf(out + pos, out_len - pos, "%02X", uid->uid[i]);
    }
}
