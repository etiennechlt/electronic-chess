/* MFRC522 driver for the Hall plus RFID demonstrator (note 27), written
 * against an abstract SPI transfer so the register logic and the
 * ISO 14443A read sequence run on a PC against a simulated chip
 * (test/test_hallrfid_demo.c). Only registers common to the NXP part and
 * its clones are used; DriverSel is never written to 00 (note 25, 4.4). */
#ifndef MFRC522_H
#define MFRC522_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* register addresses (datasheet section 9) */
enum {
    MFRC522_COMMAND = 0x01,
    MFRC522_COM_IEN = 0x02,
    MFRC522_DIV_IEN = 0x03,
    MFRC522_COM_IRQ = 0x04,
    MFRC522_DIV_IRQ = 0x05,
    MFRC522_ERROR_REG = 0x06,
    MFRC522_STATUS1 = 0x07,
    MFRC522_STATUS2 = 0x08,
    MFRC522_FIFO_DATA = 0x09,
    MFRC522_FIFO_LEVEL = 0x0A,
    MFRC522_CONTROL = 0x0C,
    MFRC522_BIT_FRAMING = 0x0D,
    MFRC522_COLL = 0x0E,
    MFRC522_MODE = 0x11,
    MFRC522_TX_MODE = 0x12,
    MFRC522_RX_MODE = 0x13,
    MFRC522_TX_CONTROL = 0x14,
    MFRC522_TX_ASK = 0x15,
    MFRC522_TX_SEL = 0x16,
    MFRC522_RX_SEL = 0x17,
    MFRC522_RX_THRESHOLD = 0x18,
    MFRC522_DEMOD = 0x19,
    MFRC522_CRC_RESULT_H = 0x21,
    MFRC522_CRC_RESULT_L = 0x22,
    MFRC522_MOD_WIDTH = 0x24,
    MFRC522_RF_CFG = 0x26,
    MFRC522_GS_N = 0x27,
    MFRC522_CW_GS_P = 0x28,
    MFRC522_MOD_GS_P = 0x29,
    MFRC522_T_MODE = 0x2A,
    MFRC522_T_PRESCALER = 0x2B,
    MFRC522_T_RELOAD_H = 0x2C,
    MFRC522_T_RELOAD_L = 0x2D,
    MFRC522_VERSION = 0x37,
};

/* CommandReg commands */
enum {
    MFRC522_CMD_IDLE = 0x00,
    MFRC522_CMD_CALC_CRC = 0x03,
    MFRC522_CMD_TRANSCEIVE = 0x0C,
    MFRC522_CMD_SOFT_RESET = 0x0F,
};

/* ComIrqReg, DivIrqReg, ErrorReg bits */
enum {
    MFRC522_IRQ_TIMER = 0x01,
    MFRC522_IRQ_ERR = 0x02,
    MFRC522_IRQ_IDLE = 0x10,
    MFRC522_IRQ_RX = 0x20,
    MFRC522_DIV_IRQ_CRC = 0x04,
    MFRC522_ERR_PROTOCOL = 0x01,
    MFRC522_ERR_PARITY = 0x02,
    MFRC522_ERR_COLL = 0x08,
    MFRC522_ERR_BUFFER_OVFL = 0x10,
};

/* TxControlReg, TxASKReg, TxSelReg fields */
enum {
    MFRC522_TX1_RF_EN = 0x01,
    MFRC522_TX2_RF_EN = 0x02,
    MFRC522_FORCE_100_ASK = 0x40,
    MFRC522_DRIVER_SEL_MASK = 0x30,
    MFRC522_DRIVER_SEL_ENCODER = 0x10,   /* the Miller encoder drives TX1 and TX2: transmitting */
    MFRC522_DRIVER_SEL_MFIN = 0x20,      /* MFIN (at PVSS) drives them: the held state, TX at 0 */
    MFRC522_MFOUT_SEL_3STATE = 0x00,
};

#define MFRC522_CW_GS_P_MAX 63u   /* CWGsP: 6 bits */

typedef enum {
    MFRC522_OK = 0,
    MFRC522_TIMEOUT,     /* no answer in the field */
    MFRC522_COLLISION,   /* two tags answered: not handled, one piece per square */
    MFRC522_ERROR,       /* protocol, parity or buffer error reported by the chip */
    MFRC522_BAD_CRC,     /* the answer's CRC_A or BCC is wrong */
    MFRC522_IO,          /* the SPI transfer failed */
} mfrc522_status_t;

/* what the board gives the driver: a full-duplex SPI transfer with NSS
 * held low for its length, the NRSTPD pin, and a millisecond wait */
typedef struct {
    void *ctx;
    bool (*xfer)(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n);
    void (*set_nrstpd)(void *ctx, bool high);
    void (*delay_ms)(void *ctx, unsigned ms);
} mfrc522_io_t;

typedef struct {
    mfrc522_io_t io;
    uint8_t version;     /* VersionReg read at wake-up */
    uint8_t cw_gs_p;     /* last conductance written */
    bool transmitting;   /* DriverSel on the encoder, carrier modulated */
} mfrc522_t;

typedef struct {
    uint8_t uid[10];
    uint8_t len;     /* 4, 7 or 10 */
    uint8_t sak;
    uint8_t atqa[2];
} mfrc522_uid_t;

/* register access */
bool mfrc522_read(mfrc522_t *d, uint8_t reg, uint8_t *value);
bool mfrc522_write(mfrc522_t *d, uint8_t reg, uint8_t value);
bool mfrc522_set_bits(mfrc522_t *d, uint8_t reg, uint8_t mask);
bool mfrc522_clear_bits(mfrc522_t *d, uint8_t reg, uint8_t mask);

/* NRSTPD high, soft reset, the ISO 14443A defaults (timer 25 ms, 100 %
 * ASK, CRC preset 6363h), transmitters enabled in the held state at the
 * conductance given; reads VersionReg into d->version. */
mfrc522_status_t mfrc522_wake(mfrc522_t *d, uint8_t cw_gs_p);
/* NRSTPD low: hard power-down, no emission, 5 uA. */
void mfrc522_power_down(mfrc522_t *d);
/* CWGsP (0..63) and CWGsN in proportion; ModGsN and ModGsP are left. */
mfrc522_status_t mfrc522_set_conductance(mfrc522_t *d, uint8_t cw_gs_p);
/* Carrier modulated by the encoder: the reader transmits and can read. */
mfrc522_status_t mfrc522_transmit(mfrc522_t *d);
/* Held: transmitters enabled, Force100ASK, DriverSel on MFIN (at PVSS),
 * TX1 and TX2 at 0. The state of every reader that is not reading. */
mfrc522_status_t mfrc522_hold(mfrc522_t *d);

/* one frame out, the answer in; `tx_bits` is the number of valid bits of
 * the last byte sent (0 means 8); *rx_len in and out */
mfrc522_status_t mfrc522_transceive(mfrc522_t *d, const uint8_t *tx, size_t tx_len, uint8_t tx_bits,
                                    uint8_t *rx, size_t *rx_len);
/* CRC_A by the chip's coprocessor, low byte first */
mfrc522_status_t mfrc522_crc(mfrc522_t *d, const uint8_t *data, size_t len, uint8_t out[2]);
/* REQA, then anticollision and SELECT through the cascade levels: the
 * UID of the one tag in the field (4, 7 or 10 bytes) */
mfrc522_status_t mfrc522_read_uid(mfrc522_t *d, mfrc522_uid_t *uid);

/* CRC_A in software (ISO 14443-3 A), for the tests and the UID check */
uint16_t mfrc522_crc_a(const uint8_t *data, size_t len);
const char *mfrc522_status_name(mfrc522_status_t s);
void mfrc522_uid_hex(const mfrc522_uid_t *uid, char *out, size_t out_len);

#endif
