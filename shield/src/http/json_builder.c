/**
 * @file json_builder.c
 * @brief JSON Builder Implementation
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/json_builder.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

/* ============================================================================
 * Constants
 * ============================================================================ */

#define INITIAL_CAPACITY 1024
#define GROWTH_FACTOR 2

/* ============================================================================
 * Internal Structure
 * ============================================================================ */

struct json_builder {
    char *buffer;
    size_t length;
    size_t capacity;
    int depth;
    bool need_comma[32];  /* Track comma need at each nesting level */
};

/* ============================================================================
 * Helpers
 * ============================================================================ */

static int ensure_capacity(json_builder_t *b, size_t additional) {
    size_t needed = b->length + additional + 1;
    if (needed <= b->capacity) return 0;
    
    size_t new_cap = b->capacity;
    while (new_cap < needed) {
        new_cap *= GROWTH_FACTOR;
    }
    
    char *new_buf = realloc(b->buffer, new_cap);
    if (!new_buf) return -1;
    
    b->buffer = new_buf;
    b->capacity = new_cap;
    return 0;
}

static int append(json_builder_t *b, const char *str) {
    size_t len = strlen(str);
    if (ensure_capacity(b, len) != 0) return -1;
    
    memcpy(b->buffer + b->length, str, len);
    b->length += len;
    b->buffer[b->length] = '\0';
    return 0;
}

static int append_char(json_builder_t *b, char c) {
    if (ensure_capacity(b, 1) != 0) return -1;
    b->buffer[b->length++] = c;
    b->buffer[b->length] = '\0';
    return 0;
}

static void maybe_comma(json_builder_t *b) {
    if (b->depth > 0 && b->need_comma[b->depth]) {
        append_char(b, ',');
    }
    b->need_comma[b->depth] = true;
}

static int append_escaped_string(json_builder_t *b, const char *str) {
    append_char(b, '"');
    
    for (const char *p = str; *p; p++) {
        switch (*p) {
            case '"':  append(b, "\\\""); break;
            case '\\': append(b, "\\\\"); break;
            case '\b': append(b, "\\b"); break;
            case '\f': append(b, "\\f"); break;
            case '\n': append(b, "\\n"); break;
            case '\r': append(b, "\\r"); break;
            case '\t': append(b, "\\t"); break;
            default:
                if ((unsigned char)*p < 0x20) {
                    char buf[8];
                    snprintf(buf, sizeof(buf), "\\u%04x", (unsigned char)*p);
                    append(b, buf);
                } else {
                    append_char(b, *p);
                }
        }
    }
    
    append_char(b, '"');
    return 0;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

json_builder_t* json_builder_create(void) {
    json_builder_t *b = calloc(1, sizeof(json_builder_t));
    if (!b) return NULL;
    
    b->buffer = malloc(INITIAL_CAPACITY);
    if (!b->buffer) {
        free(b);
        return NULL;
    }
    
    b->buffer[0] = '\0';
    b->length = 0;
    b->capacity = INITIAL_CAPACITY;
    b->depth = 0;
    
    return b;
}

void json_builder_destroy(json_builder_t *builder) {
    if (!builder) return;
    free(builder->buffer);
    free(builder);
}

const char* json_builder_get_string(json_builder_t *builder) {
    return builder ? builder->buffer : NULL;
}

size_t json_builder_get_length(json_builder_t *builder) {
    return builder ? builder->length : 0;
}

void json_builder_reset(json_builder_t *builder) {
    if (!builder) return;
    builder->length = 0;
    builder->buffer[0] = '\0';
    builder->depth = 0;
    memset(builder->need_comma, 0, sizeof(builder->need_comma));
}

/* ============================================================================
 * Object Building
 * ============================================================================ */

json_builder_t* json_object_start(json_builder_t *builder) {
    if (!builder) return NULL;
    maybe_comma(builder);
    append_char(builder, '{');
    builder->depth++;
    builder->need_comma[builder->depth] = false;
    return builder;
}

json_builder_t* json_object_end(json_builder_t *builder) {
    if (!builder) return NULL;
    builder->depth--;
    append_char(builder, '}');
    return builder;
}

json_builder_t* json_add_string(json_builder_t *builder, const char *key, const char *value) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    
    if (value) {
        append_escaped_string(builder, value);
    } else {
        append(builder, "null");
    }
    
    return builder;
}

json_builder_t* json_add_number(json_builder_t *builder, const char *key, double value) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    
    char buf[64];
    snprintf(buf, sizeof(buf), "%g", value);
    append(builder, buf);
    
    return builder;
}

json_builder_t* json_add_int(json_builder_t *builder, const char *key, long long value) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    
    char buf[32];
    snprintf(buf, sizeof(buf), "%lld", value);
    append(builder, buf);
    
    return builder;
}

json_builder_t* json_add_bool(json_builder_t *builder, const char *key, bool value) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    append(builder, value ? "true" : "false");
    
    return builder;
}

json_builder_t* json_add_null(json_builder_t *builder, const char *key) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append(builder, ":null");
    
    return builder;
}

json_builder_t* json_add_object(json_builder_t *builder, const char *key) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    append_char(builder, '{');
    
    builder->depth++;
    builder->need_comma[builder->depth] = false;
    
    return builder;
}

json_builder_t* json_add_array(json_builder_t *builder, const char *key) {
    if (!builder || !key) return NULL;
    
    maybe_comma(builder);
    append_escaped_string(builder, key);
    append_char(builder, ':');
    append_char(builder, '[');
    
    builder->depth++;
    builder->need_comma[builder->depth] = false;
    
    return builder;
}

/* ============================================================================
 * Array Building
 * ============================================================================ */

json_builder_t* json_array_start(json_builder_t *builder) {
    if (!builder) return NULL;
    maybe_comma(builder);
    append_char(builder, '[');
    builder->depth++;
    builder->need_comma[builder->depth] = false;
    return builder;
}

json_builder_t* json_array_end(json_builder_t *builder) {
    if (!builder) return NULL;
    builder->depth--;
    append_char(builder, ']');
    return builder;
}

json_builder_t* json_array_add_string(json_builder_t *builder, const char *value) {
    if (!builder) return NULL;
    
    maybe_comma(builder);
    if (value) {
        append_escaped_string(builder, value);
    } else {
        append(builder, "null");
    }
    
    return builder;
}

json_builder_t* json_array_add_number(json_builder_t *builder, double value) {
    if (!builder) return NULL;
    
    maybe_comma(builder);
    char buf[64];
    snprintf(buf, sizeof(buf), "%g", value);
    append(builder, buf);
    
    return builder;
}

json_builder_t* json_array_add_bool(json_builder_t *builder, bool value) {
    if (!builder) return NULL;
    
    maybe_comma(builder);
    append(builder, value ? "true" : "false");
    
    return builder;
}

json_builder_t* json_array_add_object(json_builder_t *builder) {
    if (!builder) return NULL;
    
    maybe_comma(builder);
    append_char(builder, '{');
    
    builder->depth++;
    builder->need_comma[builder->depth] = false;
    
    return builder;
}
