/**
 * @file json_parser.c
 * @brief Minimal JSON Parser Implementation for HTTP module
 * 
 * Uses http_json_ prefix to avoid conflicts with utils/json.c
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include "http/json_parser.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* ============================================================================
 * Parser State
 * ============================================================================ */

typedef struct {
    const char *input;
    size_t pos;
    size_t length;
    char *error;
} http_parser_state_t;

/* Forward declarations */
static http_json_value_t* parse_value(http_parser_state_t *p);
static http_json_value_t* parse_object(http_parser_state_t *p);
static http_json_value_t* parse_array(http_parser_state_t *p);
static http_json_value_t* parse_string(http_parser_state_t *p);
static http_json_value_t* parse_number(http_parser_state_t *p);
static http_json_value_t* parse_keyword(http_parser_state_t *p);
static void skip_whitespace(http_parser_state_t *p);
static char peek(http_parser_state_t *p);
static char advance(http_parser_state_t *p);
static bool match(http_parser_state_t *p, char expected);
static void set_error(http_parser_state_t *p, const char *msg);

/* ============================================================================
 * Public API
 * ============================================================================ */

http_json_value_t* http_json_parse(const char *json, char **error_msg) {
    if (!json) {
        if (error_msg) *error_msg = strdup("NULL input");
        return NULL;
    }
    
    http_parser_state_t parser = {
        .input = json,
        .pos = 0,
        .length = strlen(json),
        .error = NULL
    };
    
    skip_whitespace(&parser);
    http_json_value_t *result = parse_value(&parser);
    
    if (parser.error) {
        if (error_msg) {
            *error_msg = parser.error;
        } else {
            free(parser.error);
        }
        http_json_free(result);
        return NULL;
    }
    
    return result;
}

void http_json_free(http_json_value_t *value) {
    if (!value) return;
    
    switch (value->type) {
        case HTTP_JSON_STRING:
            free(value->data.string);
            break;
            
        case HTTP_JSON_ARRAY:
            if (value->data.array) {
                for (size_t i = 0; i < value->data.array->count; i++) {
                    http_json_free(&value->data.array->items[i]);
                }
                free(value->data.array->items);
                free(value->data.array);
            }
            break;
            
        case HTTP_JSON_OBJECT:
            if (value->data.object) {
                for (size_t i = 0; i < value->data.object->count; i++) {
                    free(value->data.object->keys[i]);
                    http_json_free(&value->data.object->values[i]);
                }
                free(value->data.object->keys);
                free(value->data.object->values);
                free(value->data.object);
            }
            break;
            
        default:
            break;
    }
    
    free(value);
}

/* ============================================================================
 * Accessors
 * ============================================================================ */

http_json_value_t* http_json_object_get(const http_json_value_t *obj, const char *key) {
    if (!obj || obj->type != HTTP_JSON_OBJECT || !key) return NULL;
    if (!obj->data.object) return NULL;
    
    for (size_t i = 0; i < obj->data.object->count; i++) {
        if (strcmp(obj->data.object->keys[i], key) == 0) {
            return &obj->data.object->values[i];
        }
    }
    return NULL;
}

const char* http_json_object_get_string(const http_json_value_t *obj, const char *key) {
    http_json_value_t *v = http_json_object_get(obj, key);
    if (v && v->type == HTTP_JSON_STRING) {
        return v->data.string;
    }
    return NULL;
}

double http_json_object_get_number(const http_json_value_t *obj, const char *key) {
    http_json_value_t *v = http_json_object_get(obj, key);
    if (v && v->type == HTTP_JSON_NUMBER) {
        return v->data.number;
    }
    return 0.0;
}

bool http_json_object_get_bool(const http_json_value_t *obj, const char *key) {
    http_json_value_t *v = http_json_object_get(obj, key);
    if (v && v->type == HTTP_JSON_BOOL) {
        return v->data.boolean;
    }
    return false;
}

http_json_array_t* http_json_object_get_array(const http_json_value_t *obj, const char *key) {
    http_json_value_t *v = http_json_object_get(obj, key);
    if (v && v->type == HTTP_JSON_ARRAY) {
        return v->data.array;
    }
    return NULL;
}

http_json_value_t* http_json_array_get(const http_json_array_t *array, size_t index) {
    if (!array || index >= array->count) return NULL;
    return &array->items[index];
}

size_t http_json_array_length(const http_json_array_t *array) {
    return array ? array->count : 0;
}

/* ============================================================================
 * Parser Helpers
 * ============================================================================ */

static void skip_whitespace(http_parser_state_t *p) {
    while (p->pos < p->length && isspace(p->input[p->pos])) {
        p->pos++;
    }
}

static char peek(http_parser_state_t *p) {
    if (p->pos >= p->length) return '\0';
    return p->input[p->pos];
}

static char advance(http_parser_state_t *p) {
    if (p->pos >= p->length) return '\0';
    return p->input[p->pos++];
}

static bool match(http_parser_state_t *p, char expected) {
    if (peek(p) == expected) {
        advance(p);
        return true;
    }
    return false;
}

static void set_error(http_parser_state_t *p, const char *msg) {
    if (!p->error) {
        char buf[256];
        snprintf(buf, sizeof(buf), "JSON parse error at position %zu: %s", p->pos, msg);
        p->error = strdup(buf);
    }
}

/* ============================================================================
 * Value Parsing
 * ============================================================================ */

static http_json_value_t* parse_value(http_parser_state_t *p) {
    skip_whitespace(p);
    
    char c = peek(p);
    
    if (c == '{') return parse_object(p);
    if (c == '[') return parse_array(p);
    if (c == '"') return parse_string(p);
    if (c == '-' || isdigit(c)) return parse_number(p);
    if (c == 't' || c == 'f' || c == 'n') return parse_keyword(p);
    
    set_error(p, "Unexpected character");
    return NULL;
}

static http_json_value_t* parse_object(http_parser_state_t *p) {
    if (!match(p, '{')) {
        set_error(p, "Expected '{'");
        return NULL;
    }
    
    http_json_value_t *value = calloc(1, sizeof(http_json_value_t));
    value->type = HTTP_JSON_OBJECT;
    value->data.object = calloc(1, sizeof(http_json_object_t));
    value->data.object->capacity = 8;
    value->data.object->keys = calloc(8, sizeof(char*));
    value->data.object->values = calloc(8, sizeof(http_json_value_t));
    
    skip_whitespace(p);
    
    if (peek(p) == '}') {
        advance(p);
        return value;
    }
    
    while (true) {
        skip_whitespace(p);
        
        if (peek(p) != '"') {
            set_error(p, "Expected string key");
            http_json_free(value);
            return NULL;
        }
        
        http_json_value_t *key_val = parse_string(p);
        if (!key_val) {
            http_json_free(value);
            return NULL;
        }
        
        char *key = key_val->data.string;
        key_val->data.string = NULL;
        http_json_free(key_val);
        
        skip_whitespace(p);
        
        if (!match(p, ':')) {
            set_error(p, "Expected ':'");
            free(key);
            http_json_free(value);
            return NULL;
        }
        
        http_json_value_t *item = parse_value(p);
        if (!item) {
            free(key);
            http_json_free(value);
            return NULL;
        }
        
        if (value->data.object->count >= value->data.object->capacity) {
            size_t new_cap = value->data.object->capacity * 2;
            value->data.object->keys = realloc(value->data.object->keys, 
                                               new_cap * sizeof(char*));
            value->data.object->values = realloc(value->data.object->values, 
                                                 new_cap * sizeof(http_json_value_t));
            value->data.object->capacity = new_cap;
        }
        
        size_t idx = value->data.object->count++;
        value->data.object->keys[idx] = key;
        value->data.object->values[idx] = *item;
        free(item);
        
        skip_whitespace(p);
        
        if (match(p, '}')) break;
        if (!match(p, ',')) {
            set_error(p, "Expected ',' or '}'");
            http_json_free(value);
            return NULL;
        }
    }
    
    return value;
}

static http_json_value_t* parse_array(http_parser_state_t *p) {
    if (!match(p, '[')) {
        set_error(p, "Expected '['");
        return NULL;
    }
    
    http_json_value_t *value = calloc(1, sizeof(http_json_value_t));
    value->type = HTTP_JSON_ARRAY;
    value->data.array = calloc(1, sizeof(http_json_array_t));
    value->data.array->capacity = 8;
    value->data.array->items = calloc(8, sizeof(http_json_value_t));
    
    skip_whitespace(p);
    
    if (peek(p) == ']') {
        advance(p);
        return value;
    }
    
    while (true) {
        http_json_value_t *item = parse_value(p);
        if (!item) {
            http_json_free(value);
            return NULL;
        }
        
        if (value->data.array->count >= value->data.array->capacity) {
            size_t new_cap = value->data.array->capacity * 2;
            value->data.array->items = realloc(value->data.array->items, 
                                               new_cap * sizeof(http_json_value_t));
            value->data.array->capacity = new_cap;
        }
        
        value->data.array->items[value->data.array->count++] = *item;
        free(item);
        
        skip_whitespace(p);
        
        if (match(p, ']')) break;
        if (!match(p, ',')) {
            set_error(p, "Expected ',' or ']'");
            http_json_free(value);
            return NULL;
        }
    }
    
    return value;
}

static http_json_value_t* parse_string(http_parser_state_t *p) {
    if (!match(p, '"')) {
        set_error(p, "Expected '\"'");
        return NULL;
    }
    
    size_t start = p->pos;
    
    while (peek(p) != '"' && peek(p) != '\0') {
        if (peek(p) == '\\') {
            advance(p);
        }
        advance(p);
    }
    
    if (peek(p) != '"') {
        set_error(p, "Unterminated string");
        return NULL;
    }
    
    size_t len = p->pos - start;
    char *str = malloc(len + 1);
    memcpy(str, p->input + start, len);
    str[len] = '\0';
    
    advance(p);
    
    http_json_value_t *value = calloc(1, sizeof(http_json_value_t));
    value->type = HTTP_JSON_STRING;
    value->data.string = str;
    
    return value;
}

static http_json_value_t* parse_number(http_parser_state_t *p) {
    size_t start = p->pos;
    
    if (peek(p) == '-') advance(p);
    
    while (isdigit(peek(p))) advance(p);
    
    if (peek(p) == '.') {
        advance(p);
        while (isdigit(peek(p))) advance(p);
    }
    
    if (peek(p) == 'e' || peek(p) == 'E') {
        advance(p);
        if (peek(p) == '+' || peek(p) == '-') advance(p);
        while (isdigit(peek(p))) advance(p);
    }
    
    size_t len = p->pos - start;
    char *num_str = malloc(len + 1);
    memcpy(num_str, p->input + start, len);
    num_str[len] = '\0';
    
    http_json_value_t *value = calloc(1, sizeof(http_json_value_t));
    value->type = HTTP_JSON_NUMBER;
    value->data.number = strtod(num_str, NULL);
    
    free(num_str);
    return value;
}

static http_json_value_t* parse_keyword(http_parser_state_t *p) {
    http_json_value_t *value = calloc(1, sizeof(http_json_value_t));
    
    if (strncmp(p->input + p->pos, "true", 4) == 0) {
        p->pos += 4;
        value->type = HTTP_JSON_BOOL;
        value->data.boolean = true;
    } else if (strncmp(p->input + p->pos, "false", 5) == 0) {
        p->pos += 5;
        value->type = HTTP_JSON_BOOL;
        value->data.boolean = false;
    } else if (strncmp(p->input + p->pos, "null", 4) == 0) {
        p->pos += 4;
        value->type = HTTP_JSON_NULL;
    } else {
        set_error(p, "Invalid keyword");
        free(value);
        return NULL;
    }
    
    return value;
}
