/*
 * SENTINEL Shield - Simple JSON Parser
 */

#ifndef SHIELD_JSON_H
#define SHIELD_JSON_H

#include "shield_common.h"

/* JSON types */
typedef enum json_type {
    JSON_NULL,
    JSON_BOOL,
    JSON_NUMBER,
    JSON_STRING,
    JSON_ARRAY,
    JSON_OBJECT,
} json_type_t;

/* JSON value */
typedef struct json_value {
    json_type_t     type;
    union {
        bool        boolean;
        double      number;
        char        *string;
        struct {
            struct json_value **items;
            int count;
        } array;
        struct {
            char **keys;
            struct json_value **values;
            int count;
        } object;
    } data;
} json_value_t;

/* Parse JSON */
json_value_t *json_parse(const char *json, size_t len);

/* Free JSON */
void json_free(json_value_t *value);

/* Get values */
json_value_t *json_get(json_value_t *obj, const char *key);
json_value_t *json_array_get(json_value_t *arr, int index);

/* Type helpers */
bool json_is_null(json_value_t *v);
bool json_is_bool(json_value_t *v);
bool json_is_number(json_value_t *v);
bool json_is_string(json_value_t *v);
bool json_is_array(json_value_t *v);
bool json_is_object(json_value_t *v);

/* Value helpers */
bool json_as_bool(json_value_t *v);
double json_as_number(json_value_t *v);
const char *json_as_string(json_value_t *v);
int json_array_length(json_value_t *v);
int json_object_length(json_value_t *v);

/* Build JSON */
json_value_t *json_new_null(void);
json_value_t *json_new_bool(bool value);
json_value_t *json_new_number(double value);
json_value_t *json_new_string(const char *value);
json_value_t *json_new_array(void);
json_value_t *json_new_object(void);

shield_err_t json_array_push(json_value_t *arr, json_value_t *value);
shield_err_t json_object_set(json_value_t *obj, const char *key, json_value_t *value);

/* Stringify */
char *json_stringify(json_value_t *value);

#endif /* SHIELD_JSON_H */
