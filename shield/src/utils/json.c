/*
 * SENTINEL Shield - JSON Parser Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_json.h"

/* Parser state */
typedef struct {
    const char *json;
    size_t len;
    size_t pos;
} parser_t;

/* Forward declarations */
static json_value_t *parse_value(parser_t *p);

/* Skip whitespace */
static void skip_ws(parser_t *p)
{
    while (p->pos < p->len && isspace((unsigned char)p->json[p->pos])) {
        p->pos++;
    }
}

/* Parse string */
static char *parse_string(parser_t *p)
{
    if (p->pos >= p->len || p->json[p->pos] != '"') {
        return NULL;
    }
    p->pos++;  /* skip opening quote */
    
    size_t start = p->pos;
    size_t len = 0;
    
    while (p->pos < p->len && p->json[p->pos] != '"') {
        if (p->json[p->pos] == '\\' && p->pos + 1 < p->len) {
            p->pos += 2;
            len += 1;
        } else {
            p->pos++;
            len++;
        }
    }
    
    if (p->pos >= p->len) return NULL;
    
    p->pos++;  /* skip closing quote */
    
    char *str = malloc(len + 1);
    if (!str) return NULL;
    
    size_t j = 0;
    for (size_t i = start; i < p->pos - 1 && j < len; i++) {
        if (p->json[i] == '\\' && i + 1 < p->pos - 1) {
            i++;
            switch (p->json[i]) {
            case 'n': str[j++] = '\n'; break;
            case 'r': str[j++] = '\r'; break;
            case 't': str[j++] = '\t'; break;
            case '"': str[j++] = '"'; break;
            case '\\': str[j++] = '\\'; break;
            default: str[j++] = p->json[i]; break;
            }
        } else {
            str[j++] = p->json[i];
        }
    }
    str[j] = '\0';
    
    return str;
}

/* Parse number */
static json_value_t *parse_number(parser_t *p)
{
    size_t start = p->pos;
    
    if (p->json[p->pos] == '-') p->pos++;
    
    while (p->pos < p->len && isdigit((unsigned char)p->json[p->pos])) {
        p->pos++;
    }
    
    if (p->pos < p->len && p->json[p->pos] == '.') {
        p->pos++;
        while (p->pos < p->len && isdigit((unsigned char)p->json[p->pos])) {
            p->pos++;
        }
    }
    
    if (p->pos < p->len && (p->json[p->pos] == 'e' || p->json[p->pos] == 'E')) {
        p->pos++;
        if (p->pos < p->len && (p->json[p->pos] == '+' || p->json[p->pos] == '-')) {
            p->pos++;
        }
        while (p->pos < p->len && isdigit((unsigned char)p->json[p->pos])) {
            p->pos++;
        }
    }
    
    char buf[64];
    size_t len = p->pos - start;
    if (len >= sizeof(buf)) len = sizeof(buf) - 1;
    memcpy(buf, p->json + start, len);
    buf[len] = '\0';
    
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (!v) return NULL;
    
    v->type = JSON_NUMBER;
    v->data.number = atof(buf);
    
    return v;
}

/* Parse array */
static json_value_t *parse_array(parser_t *p)
{
    if (p->pos >= p->len || p->json[p->pos] != '[') {
        return NULL;
    }
    p->pos++;
    
    json_value_t *arr = json_new_array();
    if (!arr) return NULL;
    
    skip_ws(p);
    
    if (p->pos < p->len && p->json[p->pos] == ']') {
        p->pos++;
        return arr;
    }
    
    while (1) {
        skip_ws(p);
        json_value_t *item = parse_value(p);
        if (!item) {
            json_free(arr);
            return NULL;
        }
        
        json_array_push(arr, item);
        
        skip_ws(p);
        if (p->pos >= p->len) {
            json_free(arr);
            return NULL;
        }
        
        if (p->json[p->pos] == ']') {
            p->pos++;
            return arr;
        }
        
        if (p->json[p->pos] != ',') {
            json_free(arr);
            return NULL;
        }
        p->pos++;
    }
}

/* Parse object */
static json_value_t *parse_object(parser_t *p)
{
    if (p->pos >= p->len || p->json[p->pos] != '{') {
        return NULL;
    }
    p->pos++;
    
    json_value_t *obj = json_new_object();
    if (!obj) return NULL;
    
    skip_ws(p);
    
    if (p->pos < p->len && p->json[p->pos] == '}') {
        p->pos++;
        return obj;
    }
    
    while (1) {
        skip_ws(p);
        char *key = parse_string(p);
        if (!key) {
            json_free(obj);
            return NULL;
        }
        
        skip_ws(p);
        if (p->pos >= p->len || p->json[p->pos] != ':') {
            free(key);
            json_free(obj);
            return NULL;
        }
        p->pos++;
        
        skip_ws(p);
        json_value_t *value = parse_value(p);
        if (!value) {
            free(key);
            json_free(obj);
            return NULL;
        }
        
        json_object_set(obj, key, value);
        free(key);
        
        skip_ws(p);
        if (p->pos >= p->len) {
            json_free(obj);
            return NULL;
        }
        
        if (p->json[p->pos] == '}') {
            p->pos++;
            return obj;
        }
        
        if (p->json[p->pos] != ',') {
            json_free(obj);
            return NULL;
        }
        p->pos++;
    }
}

/* Parse value */
static json_value_t *parse_value(parser_t *p)
{
    skip_ws(p);
    
    if (p->pos >= p->len) return NULL;
    
    char c = p->json[p->pos];
    
    if (c == '"') {
        char *str = parse_string(p);
        if (!str) return NULL;
        json_value_t *v = calloc(1, sizeof(json_value_t));
        v->type = JSON_STRING;
        v->data.string = str;
        return v;
    }
    
    if (c == '[') return parse_array(p);
    if (c == '{') return parse_object(p);
    
    if (c == '-' || isdigit((unsigned char)c)) {
        return parse_number(p);
    }
    
    if (strncmp(p->json + p->pos, "true", 4) == 0) {
        p->pos += 4;
        return json_new_bool(true);
    }
    
    if (strncmp(p->json + p->pos, "false", 5) == 0) {
        p->pos += 5;
        return json_new_bool(false);
    }
    
    if (strncmp(p->json + p->pos, "null", 4) == 0) {
        p->pos += 4;
        return json_new_null();
    }
    
    return NULL;
}

/* Public API */

json_value_t *json_parse(const char *json, size_t len)
{
    if (!json) return NULL;
    
    parser_t p = {json, len > 0 ? len : strlen(json), 0};
    return parse_value(&p);
}

void json_free(json_value_t *value)
{
    if (!value) return;
    
    switch (value->type) {
    case JSON_STRING:
        free(value->data.string);
        break;
    case JSON_ARRAY:
        for (int i = 0; i < value->data.array.count; i++) {
            json_free(value->data.array.items[i]);
        }
        free(value->data.array.items);
        break;
    case JSON_OBJECT:
        for (int i = 0; i < value->data.object.count; i++) {
            free(value->data.object.keys[i]);
            json_free(value->data.object.values[i]);
        }
        free(value->data.object.keys);
        free(value->data.object.values);
        break;
    default:
        break;
    }
    
    free(value);
}

json_value_t *json_get(json_value_t *obj, const char *key)
{
    if (!obj || obj->type != JSON_OBJECT || !key) return NULL;
    
    for (int i = 0; i < obj->data.object.count; i++) {
        if (strcmp(obj->data.object.keys[i], key) == 0) {
            return obj->data.object.values[i];
        }
    }
    
    return NULL;
}

json_value_t *json_array_get(json_value_t *arr, int index)
{
    if (!arr || arr->type != JSON_ARRAY) return NULL;
    if (index < 0 || index >= arr->data.array.count) return NULL;
    return arr->data.array.items[index];
}

bool json_is_null(json_value_t *v) { return v && v->type == JSON_NULL; }
bool json_is_bool(json_value_t *v) { return v && v->type == JSON_BOOL; }
bool json_is_number(json_value_t *v) { return v && v->type == JSON_NUMBER; }
bool json_is_string(json_value_t *v) { return v && v->type == JSON_STRING; }
bool json_is_array(json_value_t *v) { return v && v->type == JSON_ARRAY; }
bool json_is_object(json_value_t *v) { return v && v->type == JSON_OBJECT; }

bool json_as_bool(json_value_t *v) { return v && v->type == JSON_BOOL ? v->data.boolean : false; }
double json_as_number(json_value_t *v) { return v && v->type == JSON_NUMBER ? v->data.number : 0; }
const char *json_as_string(json_value_t *v) { return v && v->type == JSON_STRING ? v->data.string : ""; }
int json_array_length(json_value_t *v) { return v && v->type == JSON_ARRAY ? v->data.array.count : 0; }
int json_object_length(json_value_t *v) { return v && v->type == JSON_OBJECT ? v->data.object.count : 0; }

json_value_t *json_new_null(void)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) v->type = JSON_NULL;
    return v;
}

json_value_t *json_new_bool(bool value)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) {
        v->type = JSON_BOOL;
        v->data.boolean = value;
    }
    return v;
}

json_value_t *json_new_number(double value)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) {
        v->type = JSON_NUMBER;
        v->data.number = value;
    }
    return v;
}

json_value_t *json_new_string(const char *value)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) {
        v->type = JSON_STRING;
        v->data.string = value ? strdup(value) : strdup("");
    }
    return v;
}

json_value_t *json_new_array(void)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) v->type = JSON_ARRAY;
    return v;
}

json_value_t *json_new_object(void)
{
    json_value_t *v = calloc(1, sizeof(json_value_t));
    if (v) v->type = JSON_OBJECT;
    return v;
}

shield_err_t json_array_push(json_value_t *arr, json_value_t *value)
{
    if (!arr || arr->type != JSON_ARRAY || !value) {
        return SHIELD_ERR_INVALID;
    }
    
    int new_count = arr->data.array.count + 1;
    json_value_t **new_items = realloc(arr->data.array.items,
                                        new_count * sizeof(json_value_t *));
    if (!new_items) return SHIELD_ERR_NOMEM;
    
    arr->data.array.items = new_items;
    arr->data.array.items[arr->data.array.count] = value;
    arr->data.array.count = new_count;
    
    return SHIELD_OK;
}

shield_err_t json_object_set(json_value_t *obj, const char *key, json_value_t *value)
{
    if (!obj || obj->type != JSON_OBJECT || !key || !value) {
        return SHIELD_ERR_INVALID;
    }
    
    int new_count = obj->data.object.count + 1;
    
    char **new_keys = realloc(obj->data.object.keys, new_count * sizeof(char *));
    json_value_t **new_values = realloc(obj->data.object.values,
                                          new_count * sizeof(json_value_t *));
    
    if (!new_keys || !new_values) {
        return SHIELD_ERR_NOMEM;
    }
    
    obj->data.object.keys = new_keys;
    obj->data.object.values = new_values;
    obj->data.object.keys[obj->data.object.count] = strdup(key);
    obj->data.object.values[obj->data.object.count] = value;
    obj->data.object.count = new_count;
    
    return SHIELD_OK;
}

/* Stringify (simplified) */
char *json_stringify(json_value_t *value)
{
    if (!value) return strdup("null");
    
    char buf[1024];
    
    switch (value->type) {
    case JSON_NULL:
        return strdup("null");
    case JSON_BOOL:
        return strdup(value->data.boolean ? "true" : "false");
    case JSON_NUMBER:
        snprintf(buf, sizeof(buf), "%g", value->data.number);
        return strdup(buf);
    case JSON_STRING:
        snprintf(buf, sizeof(buf), "\"%s\"", value->data.string);
        return strdup(buf);
    case JSON_ARRAY:
    case JSON_OBJECT:
        /* TODO: full implementation */
        return strdup(value->type == JSON_ARRAY ? "[]" : "{}");
    default:
        return strdup("null");
    }
}
