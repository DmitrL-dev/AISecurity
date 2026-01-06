/**
 * @file json_parser.h
 * @brief Minimal JSON Parser for Shield REST API
 * 
 * Lightweight, zero-dependency JSON parser.
 * Supports: objects, arrays, strings, numbers, booleans, null.
 * 
 * Note: Uses http_json_ prefix to avoid conflicts with utils/json.c
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_HTTP_JSON_PARSER_H
#define SHIELD_HTTP_JSON_PARSER_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * JSON Value Types
 * ============================================================================ */

typedef enum {
    HTTP_JSON_NULL,
    HTTP_JSON_BOOL,
    HTTP_JSON_NUMBER,
    HTTP_JSON_STRING,
    HTTP_JSON_ARRAY,
    HTTP_JSON_OBJECT
} http_json_type_t;

/* ============================================================================
 * JSON Value
 * ============================================================================ */

typedef struct http_json_value http_json_value_t;
typedef struct http_json_object http_json_object_t;
typedef struct http_json_array http_json_array_t;

struct http_json_value {
    http_json_type_t type;
    union {
        bool boolean;
        double number;
        char *string;
        http_json_array_t *array;
        http_json_object_t *object;
    } data;
};

struct http_json_object {
    char **keys;
    http_json_value_t *values;
    size_t count;
    size_t capacity;
};

struct http_json_array {
    http_json_value_t *items;
    size_t count;
    size_t capacity;
};

/* ============================================================================
 * Parsing
 * ============================================================================ */

/**
 * @brief Parse JSON string
 */
http_json_value_t* http_json_parse(const char *json, char **error_msg);

/**
 * @brief Free JSON value
 */
void http_json_free(http_json_value_t *value);

/* ============================================================================
 * Accessors
 * ============================================================================ */

http_json_value_t* http_json_object_get(const http_json_value_t *obj, const char *key);
const char* http_json_object_get_string(const http_json_value_t *obj, const char *key);
double http_json_object_get_number(const http_json_value_t *obj, const char *key);
bool http_json_object_get_bool(const http_json_value_t *obj, const char *key);
http_json_array_t* http_json_object_get_array(const http_json_value_t *obj, const char *key);
http_json_value_t* http_json_array_get(const http_json_array_t *array, size_t index);
size_t http_json_array_length(const http_json_array_t *array);

/* ============================================================================
 * Type Checking
 * ============================================================================ */

static inline bool http_json_is_null(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_NULL;
}

static inline bool http_json_is_bool(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_BOOL;
}

static inline bool http_json_is_number(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_NUMBER;
}

static inline bool http_json_is_string(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_STRING;
}

static inline bool http_json_is_array(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_ARRAY;
}

static inline bool http_json_is_object(const http_json_value_t *v) {
    return v && v->type == HTTP_JSON_OBJECT;
}

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_HTTP_JSON_PARSER_H */
