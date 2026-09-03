/* Calibration storage in the last flash page (0x0807F800) and the
 * nearest-neighbor classifier of the brief (3.3). */

#include "app.h"

#define CALIB_ADDR 0x0807F800u
#define CALIB_MAGIC 0x4C43414Cu /* "LCAL" */
#define CALIB_PAGE_SIZE 2048u   /* dual-bank G474: 2K pages */

static uint32_t crc32_soft(const uint32_t *words, uint32_t n) {
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < n; i++) {
        crc ^= words[i];
        for (uint32_t b = 0; b < 32u; b++) {
            crc = (crc >> 1u) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return ~crc;
}

bool calib_load(calib_t *out) {
    const calib_t *stored = (const calib_t *)CALIB_ADDR;
    if (stored->magic != CALIB_MAGIC) {
        return false;
    }
    if (crc32_soft((const uint32_t *)stored, 1u + N_SQUARES) != stored->crc) {
        return false;
    }
    *out = *stored;
    return true;
}

static void flash_unlock(void) {
    if (FLASH->CR & FLASH_CR_LOCK) {
        FLASH->KEYR = 0x45670123u;
        FLASH->KEYR = 0xCDEF89ABu;
    }
}

bool calib_store(const calib_t *cal) {
    calib_t tmp = *cal;
    tmp.magic = CALIB_MAGIC;
    tmp.crc = crc32_soft((const uint32_t *)&tmp, 1u + N_SQUARES);

    flash_unlock();
    while (FLASH->SR & FLASH_SR_BSY) {
    }
    FLASH->SR = FLASH->SR; /* clear stale error flags */

    /* Erase the calibration page (bank 2, last page). */
    uint32_t page = (CALIB_ADDR - 0x08000000u) / CALIB_PAGE_SIZE;
    FLASH->CR = FLASH_CR_PER | ((page & 0x7Fu) << FLASH_CR_PNB_Pos) |
                ((page > 127u) ? FLASH_CR_BKER : 0u);
    FLASH->CR |= FLASH_CR_STRT;
    while (FLASH->SR & FLASH_SR_BSY) {
    }
    FLASH->CR &= ~FLASH_CR_PER;

    /* Program by 64-bit double words. */
    const uint64_t *src = (const uint64_t *)&tmp;
    volatile uint64_t *dst = (volatile uint64_t *)CALIB_ADDR;
    uint32_t n64 = (sizeof(calib_t) + 7u) / 8u;
    FLASH->CR |= FLASH_CR_PG;
    for (uint32_t i = 0; i < n64; i++) {
        dst[i] = src[i];
        while (FLASH->SR & FLASH_SR_BSY) {
        }
    }
    FLASH->CR &= ~FLASH_CR_PG;
    FLASH->CR |= FLASH_CR_LOCK;

    calib_t check;
    return calib_load(&check);
}

int calib_classify(const calib_t *cal, uint32_t f_hz) {
    int best = -1;
    uint32_t best_d = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < N_SQUARES; i++) {
        uint32_t ref = cal->freq_hz[i];
        uint32_t d = (f_hz > ref) ? f_hz - ref : ref - f_hz;
        if (d < best_d) {
            best_d = d;
            best = (int)i;
        }
    }
    return best;
}
