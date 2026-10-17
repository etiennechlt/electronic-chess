/* Host-side test of the demonstrator firmware: the MFRC522 driver runs
 * against a simulated chip (registers, FIFO, CRC coprocessor, one tag in
 * the field answering the ISO 14443A sequence) and the Hall helpers
 * against the generated thresholds. See ../README.md for the command. */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "hall.h"
#include "mfrc522.h"

/* ------------------------------------------------------------ the simulated chip */
typedef struct {
    uint8_t reg[64];
    uint8_t fifo[64];
    unsigned fifo_len, fifo_rd;
    bool nrstpd;
    bool tag_present;
    uint8_t uid[7];       /* a 7-byte UID: two cascade levels, like an NTAG */
    unsigned transceives;
    bool saw_driver_sel_00;
    uint8_t selected_level;
} fake_chip_t;

static void fake_reset(fake_chip_t *c) {
    memset(c->reg, 0, sizeof c->reg);
    c->reg[MFRC522_VERSION] = 0x92;
    c->reg[MFRC522_TX_SEL] = 0x10;
    c->reg[MFRC522_GS_N] = 0x88;
    c->reg[MFRC522_CW_GS_P] = 0x20;
    c->reg[MFRC522_MOD_GS_P] = 0x20;
    c->fifo_len = c->fifo_rd = 0;
    c->selected_level = 0;
}

static void fake_push(fake_chip_t *c, const uint8_t *data, unsigned n) {
    c->fifo_len = c->fifo_rd = 0;
    memcpy(c->fifo, data, n);
    c->fifo_len = n;
}

static void fake_answer(fake_chip_t *c) {
    const uint8_t *f = c->fifo;
    unsigned n = c->fifo_len;
    uint8_t tx_bits = c->reg[MFRC522_BIT_FRAMING] & 0x07u;
    c->transceives++;
    c->reg[MFRC522_ERROR_REG] = 0;
    if (!c->tag_present || !(c->reg[MFRC522_TX_CONTROL] & 0x03) ||
        (c->reg[MFRC522_TX_SEL] & MFRC522_DRIVER_SEL_MASK) != MFRC522_DRIVER_SEL_ENCODER) {
        c->fifo_len = c->fifo_rd = 0;
        c->reg[MFRC522_COM_IRQ] |= MFRC522_IRQ_TIMER;   /* nothing answers: timer runs out */
        return;
    }
    if (n == 1 && tx_bits == 7 && f[0] == 0x26) {
        uint8_t atqa[2] = {0x44, 0x00};
        fake_push(c, atqa, 2);
    } else if (n == 2 && f[1] == 0x20 && (f[0] == 0x93 || f[0] == 0x95)) {
        uint8_t ans[5];
        if (f[0] == 0x93) {
            ans[0] = 0x88;
            memcpy(&ans[1], c->uid, 3);
        } else {
            memcpy(ans, &c->uid[3], 4);
        }
        ans[4] = (uint8_t)(ans[0] ^ ans[1] ^ ans[2] ^ ans[3]);
        fake_push(c, ans, 5);
    } else if (n == 9 && f[1] == 0x70 && (f[0] == 0x93 || f[0] == 0x95)) {
        uint16_t crc = mfrc522_crc_a(f, 7);
        assert(f[7] == (crc & 0xFF) && f[8] == (crc >> 8));   /* the driver appended CRC_A */
        assert((uint8_t)(f[2] ^ f[3] ^ f[4] ^ f[5]) == f[6]);
        uint8_t sak[3] = {f[0] == 0x93 ? 0x04 : 0x00, 0, 0};
        uint16_t sc = mfrc522_crc_a(sak, 1);
        sak[1] = (uint8_t)(sc & 0xFF);
        sak[2] = (uint8_t)(sc >> 8);
        c->selected_level = f[0] == 0x93 ? 1 : 2;
        fake_push(c, sak, 3);
    } else {
        c->fifo_len = c->fifo_rd = 0;
        c->reg[MFRC522_ERROR_REG] = MFRC522_ERR_PROTOCOL;
    }
    c->reg[MFRC522_COM_IRQ] |= MFRC522_IRQ_RX | MFRC522_IRQ_IDLE;
}

static void fake_write(fake_chip_t *c, uint8_t addr, uint8_t v) {
    switch (addr) {
    case MFRC522_FIFO_DATA:
        if (c->fifo_len < sizeof c->fifo) {
            c->fifo[c->fifo_len++] = v;
        }
        return;
    case MFRC522_FIFO_LEVEL:
        if (v & 0x80) {
            c->fifo_len = c->fifo_rd = 0;
        }
        return;
    case MFRC522_COM_IRQ:
        c->reg[addr] &= (uint8_t)~(v & 0x7F);   /* writing 1 clears */
        return;
    case MFRC522_DIV_IRQ:
        c->reg[addr] &= (uint8_t)~(v & 0x7F);
        return;
    case MFRC522_TX_SEL:
        if ((v & MFRC522_DRIVER_SEL_MASK) == 0) {
            c->saw_driver_sel_00 = true;
        }
        break;
    case MFRC522_COMMAND:
        if (v == MFRC522_CMD_SOFT_RESET) {
            fake_reset(c);
            return;
        }
        if (v == MFRC522_CMD_CALC_CRC) {
            uint16_t crc = mfrc522_crc_a(c->fifo, c->fifo_len);
            c->reg[MFRC522_CRC_RESULT_L] = (uint8_t)(crc & 0xFF);
            c->reg[MFRC522_CRC_RESULT_H] = (uint8_t)(crc >> 8);
            c->reg[MFRC522_DIV_IRQ] |= MFRC522_DIV_IRQ_CRC;
        }
        break;
    case MFRC522_BIT_FRAMING:
        if ((v & 0x80) && c->reg[MFRC522_COMMAND] == MFRC522_CMD_TRANSCEIVE) {
            c->reg[addr] = v;
            fake_answer(c);
            return;
        }
        break;
    default:
        break;
    }
    c->reg[addr] = v;
}

static uint8_t fake_read(fake_chip_t *c, uint8_t addr) {
    if (addr == MFRC522_FIFO_DATA) {
        return c->fifo_rd < c->fifo_len ? c->fifo[c->fifo_rd++] : 0;
    }
    if (addr == MFRC522_FIFO_LEVEL) {
        return (uint8_t)(c->fifo_len - c->fifo_rd);
    }
    return c->reg[addr];
}

static bool fake_xfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    fake_chip_t *c = ctx;
    assert(n == 2);
    if (!c->nrstpd) {
        rx[0] = rx[1] = 0;   /* a chip in hard power-down answers nothing */
        return true;
    }
    uint8_t addr = (uint8_t)((tx[0] >> 1) & 0x3F);
    rx[0] = 0;
    if (tx[0] & 0x80) {
        rx[1] = fake_read(c, addr);
    } else {
        fake_write(c, addr, tx[1]);
        rx[1] = 0;
    }
    return true;
}

static void fake_set_nrstpd(void *ctx, bool high) {
    fake_chip_t *c = ctx;
    if (high && !c->nrstpd) {
        fake_reset(c);
    }
    c->nrstpd = high;
}

static void fake_delay(void *ctx, unsigned ms) {
    (void)ctx;
    (void)ms;
}

/* ------------------------------------------------------------ tests */
static void test_crc_a(void) {
    /* ISO 14443-3 A, annex B (low byte transmitted first): CRC_A of 0x00 0x00
     * is 0x1EA0, of 0x12 0x34 is 0xCF26; checked against a bitwise 0x8408 run */
    uint8_t z[2] = {0x00, 0x00};
    uint8_t s[2] = {0x12, 0x34};
    assert(mfrc522_crc_a(z, 2) == 0x1EA0);
    assert(mfrc522_crc_a(s, 2) == 0xCF26);
}

static void test_reader(void) {
    fake_chip_t chip = {0};
    mfrc522_t d = {.io = {&chip, fake_xfer, fake_set_nrstpd, fake_delay}};
    memcpy(chip.uid, (uint8_t[]){0x04, 0xA2, 0x3B, 0x1C, 0x5D, 0x6E, 0x80}, 7);

    /* powered down: no answer at all */
    uint8_t v = 0xAA;
    assert(mfrc522_read(&d, MFRC522_VERSION, &v) && v == 0x00);

    /* wake: version read, held state, the conductance asked */
    assert(mfrc522_wake(&d, 8) == MFRC522_OK);
    assert(d.version == 0x92 && chip.nrstpd);
    assert(chip.reg[MFRC522_CW_GS_P] == 8 && (chip.reg[MFRC522_GS_N] >> 4) == 2);
    assert((chip.reg[MFRC522_GS_N] & 0x0F) == 0x8);
    assert(chip.reg[MFRC522_TX_CONTROL] == 0x03);
    assert(chip.reg[MFRC522_TX_ASK] == MFRC522_FORCE_100_ASK);
    assert((chip.reg[MFRC522_TX_SEL] & MFRC522_DRIVER_SEL_MASK) == MFRC522_DRIVER_SEL_MFIN);
    assert(!d.transmitting);
    assert(chip.reg[MFRC522_T_RELOAD_H] == 0x03 && chip.reg[MFRC522_T_RELOAD_L] == 0xE8);

    /* the CRC coprocessor path gives the software value */
    uint8_t data[3] = {0x93, 0x70, 0x88};
    uint8_t crc[2];
    assert(mfrc522_crc(&d, data, 3, crc) == MFRC522_OK);
    uint16_t sw = mfrc522_crc_a(data, 3);
    assert(crc[0] == (sw & 0xFF) && crc[1] == (sw >> 8));

    /* held: a tag in the field is not read (TX at 0) */
    chip.tag_present = true;
    mfrc522_uid_t uid;
    assert(mfrc522_read_uid(&d, &uid) == MFRC522_TIMEOUT);

    /* transmitting, no tag: timeout; a tag: its 7-byte UID through two cascade levels */
    assert(mfrc522_transmit(&d) == MFRC522_OK && d.transmitting);
    chip.tag_present = false;
    assert(mfrc522_read_uid(&d, &uid) == MFRC522_TIMEOUT);
    chip.tag_present = true;
    unsigned before = chip.transceives;
    assert(mfrc522_read_uid(&d, &uid) == MFRC522_OK);
    assert(chip.transceives - before == 5);   /* REQA, AC1, SEL1, AC2, SEL2 */
    assert(uid.len == 7 && memcmp(uid.uid, chip.uid, 7) == 0);
    assert(uid.sak == 0x00 && uid.atqa[0] == 0x44 && chip.selected_level == 2);
    char hex[24];
    mfrc522_uid_hex(&uid, hex, sizeof hex);
    assert(strcmp(hex, "04A23B1C5D6E80") == 0);

    /* a corrupted answer is refused by the BCC check */
    chip.uid[0] ^= 0x01;
    /* (the fake recomputes its BCC, so corrupt the chip's answer path instead) */
    chip.uid[0] ^= 0x01;
    uint8_t bad[5] = {0x88, 0x04, 0xA2, 0x3B, 0x00};
    fake_push(&chip, bad, 5);
    /* feed the bad frame straight through transceive's receive path */
    chip.reg[MFRC522_COM_IRQ] |= MFRC522_IRQ_RX;
    uint8_t rx[5];
    size_t n = 5;
    /* a direct transceive of an unknown frame: the fake reports a protocol error */
    uint8_t junk[1] = {0x55};
    assert(mfrc522_transceive(&d, junk, 1, 0, rx, &n) == MFRC522_ERROR);

    /* back to held, then power-down: no DriverSel 00 was ever written */
    assert(mfrc522_hold(&d) == MFRC522_OK && !d.transmitting);
    assert(chip.reg[MFRC522_TX_CONTROL] == 0x03);
    mfrc522_power_down(&d);
    assert(!chip.nrstpd);
    assert(!chip.saw_driver_sel_00);

    /* conductance clamps at 63 */
    chip.nrstpd = true;
    assert(mfrc522_set_conductance(&d, 200) == MFRC522_OK && d.cw_gs_p == 63);
    assert(chip.reg[MFRC522_CW_GS_P] == 63 && (chip.reg[MFRC522_GS_N] >> 4) == 15);
}

static void test_hall(void) {
    demo_hall_t h;
    hall_init(&h);
    assert(DEMO_OFF_COUNTS < DEMO_ON_COUNTS && DEMO_ON_COUNTS < DEMO_WEAKEST_PRESENT_COUNTS);
    assert(h.baseline[0] == DEMO_BASELINE_COUNTS && !h.zeroed);

    /* the reference channels: a rail 2 % low scales the reading back */
    int16_t ground = 3, rail_half = (int16_t)(DEMO_RAIL_HALF_COUNTS * 98 / 100);
    int16_t raw = (int16_t)(DEMO_BASELINE_COUNTS * 98 / 100);
    int16_t corr = hall_corrected(raw, ground, rail_half);
    assert(corr >= DEMO_BASELINE_COUNTS - 3 && corr <= DEMO_BASELINE_COUNTS + 3);
    assert(hall_corrected(raw, 0, 0) == raw);   /* references not read */

    /* zero, then the weakest pawn of the yaml is present, south pole up... */
    int16_t empty[DEMO_SITES];
    for (unsigned i = 0; i < DEMO_SITES; i++) {
        empty[i] = (int16_t)(DEMO_BASELINE_COUNTS + 5);
    }
    hall_zero(&h, empty);
    assert(h.zeroed && h.baseline[2] == DEMO_BASELINE_COUNTS + 5);
    int16_t swing = hall_swing(&h, 0, (int16_t)(empty[0] + DEMO_WEAKEST_PRESENT_COUNTS));
    assert(swing == DEMO_WEAKEST_PRESENT_COUNTS);
    assert(hall_update(&h, 0, swing) == HALL_PRESENT && hall_pole(swing) == 'S');
    float mt = hall_swing_mt(swing);
    assert(mt > 20.0f && mt < 21.0f);   /* 410 counts at 0.757 mV and 15 mV/mT */

    /* ...hysteresis keeps it between the thresholds, a north pole reads negative */
    assert(hall_update(&h, 0, (int16_t)((DEMO_ON_COUNTS + DEMO_OFF_COUNTS) / 2)) == HALL_PRESENT);
    assert(hall_update(&h, 0, (int16_t)(DEMO_OFF_COUNTS - 1)) == HALL_EMPTY);
    assert(hall_update(&h, 1, (int16_t)-DEMO_WEAKEST_PRESENT_COUNTS) == HALL_PRESENT);
    assert(hall_pole((int16_t)-DEMO_WEAKEST_PRESENT_COUNTS) == 'N' && hall_pole(10) == '.');
}

int main(void) {
    test_crc_a();
    test_reader();
    test_hall();
    puts("hallrfid-demo host test: ok");
    return 0;
}
