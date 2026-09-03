/* Line protocol shared by the board, the bridge and the clock (see
 * docs/notes/12-protocole.md). One ASCII line per message, fields
 * separated by commas, the first field is the type letter. */
#ifndef PROTO_H
#define PROTO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PROTO_LINE_MAX 128
#define PROTO_FIELDS_MAX 8

typedef struct {
    char type;
    int n;                            /* number of fields after the type */
    const char *field[PROTO_FIELDS_MAX];
    char buf[PROTO_LINE_MAX];
} proto_msg_t;

/* Splits a line (without its newline) into fields; returns false when the
 * line is empty or malformed. Fields point into msg->buf. */
bool proto_parse(const char *line, proto_msg_t *msg);

/* Accumulates bytes and calls `on_line` for each complete line. */
typedef struct {
    char buf[PROTO_LINE_MAX];
    size_t len;
    uint32_t dropped;                 /* overlong or malformed lines */
} proto_reader_t;

void proto_reader_feed(proto_reader_t *r, const uint8_t *data, size_t n,
                       void (*on_line)(const char *line, void *ctx), void *ctx);

#endif
