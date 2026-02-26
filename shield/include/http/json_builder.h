/**
 * @file json_builder.h
 * @brief JSON Builder for Shield REST API
 * 
 * Fluent API for building JSON responses.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_JSON_BUILDER_H
#define SHIELD_JSON_BUILDER_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * JSON Builder
 * ============================================================================ */

typedef struct json_builder json_builder_t;

/**
 * @brief Create JSON builder
 */
json_builder_t* json_builder_create(void);

/**
 * @brief Destroy builder and free memory
 */
void json_builder_destroy(json_builder_t *builder);

/**
 * @brief Get built JSON string
 * 
 * @param builder Builder instance
 * @return JSON string (owned by builder, do not free)
 */
const char* json_builder_get_string(json_builder_t *builder);

/**
 * @brief Get string length
 */
size_t json_builder_get_length(json_builder_t *builder);

/**
 * @brief Reset builder for reuse
 */
void json_builder_reset(json_builder_t *builder);

/* ============================================================================
 * Object Building
 * ============================================================================ */

/**
 * @brief Start object
 */
json_builder_t* json_object_start(json_builder_t *builder);

/**
 * @brief End object
 */
json_builder_t* json_object_end(json_builder_t *builder);

/**
 * @brief Add string property
 */
json_builder_t* json_add_string(json_builder_t *builder, const char *key, const char *value);

/**
 * @brief Add number property
 */
json_builder_t* json_add_number(json_builder_t *builder, const char *key, double value);

/**
 * @brief Add integer property
 */
json_builder_t* json_add_int(json_builder_t *builder, const char *key, long long value);

/**
 * @brief Add boolean property
 */
json_builder_t* json_add_bool(json_builder_t *builder, const char *key, bool value);

/**
 * @brief Add null property
 */
json_builder_t* json_add_null(json_builder_t *builder, const char *key);

/**
 * @brief Start nested object
 */
json_builder_t* json_add_object(json_builder_t *builder, const char *key);

/**
 * @brief Start nested array
 */
json_builder_t* json_add_array(json_builder_t *builder, const char *key);

/* ============================================================================
 * Array Building
 * ============================================================================ */

/**
 * @brief Start array
 */
json_builder_t* json_array_start(json_builder_t *builder);

/**
 * @brief End array
 */
json_builder_t* json_array_end(json_builder_t *builder);

/**
 * @brief Add string to array
 */
json_builder_t* json_array_add_string(json_builder_t *builder, const char *value);

/**
 * @brief Add number to array
 */
json_builder_t* json_array_add_number(json_builder_t *builder, double value);

/**
 * @brief Add boolean to array
 */
json_builder_t* json_array_add_bool(json_builder_t *builder, bool value);

/**
 * @brief Start nested object in array
 */
json_builder_t* json_array_add_object(json_builder_t *builder);

/* ============================================================================
 * Convenience Macros
 * ============================================================================ */

/**
 * @brief Build simple success response
 * 
 * Usage:
 *   const char *json = JSON_SUCCESS_RESPONSE("Operation completed");
 */
#define JSON_SUCCESS_RESPONSE(msg) \
    "{\"success\":true,\"message\":\"" msg "\"}"

/**
 * @brief Build simple error response
 */
#define JSON_ERROR_RESPONSE(code, msg) \
    "{\"error\":{\"code\":" #code ",\"message\":\"" msg "\"}}"

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_JSON_BUILDER_H */
