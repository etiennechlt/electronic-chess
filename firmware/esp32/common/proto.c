#include "proto.h"

#include <string.h>

bool proto_parse(const char *line, proto_msg_t *msg) {
    size_t len = strlen(line);
    if (len == 0 || len >= PROTO_LINE_MAX) {
        return false;
    }
    memcpy(msg->buf, line, len + 1);
    msg->type = msg->buf[0];
    msg->n = 0;
    if (msg->buf[1] == '\0') {
        return true;
    }
    if (msg->buf[1] != ',') {
        return false;
    }
    char *p = msg->buf + 2;
    while (p && msg->n < PROTO_FIELDS_MAX) {
        msg->field[msg->n++] = p;
        char *comma = strchr(p, ',');
        if (comma) {
            *comma = '\0';
            p = comma + 1;
        } else {
            p = NULL;
        }
    }
    return true;
}

void proto_reader_feed(proto_reader_t *r, const uint8_t *data, size_t n,
                       void (*on_line)(const char *line, void *ctx), void *ctx) {
    for (size_t i = 0; i < n; i++) {
        char c = (char)data[i];
        if (c == '\r') {
            continue;
        }
        if (c == '\n') {
            r->buf[r->len] = '\0';
            if (r->len > 0) {
                on_line(r->buf, ctx);
            }
            r->len = 0;
            continue;
        }
        if (r->len + 1 >= PROTO_LINE_MAX) {
            r->dropped++;
            r->len = 0;
            continue;
        }
        r->buf[r->len++] = c;
    }
}
