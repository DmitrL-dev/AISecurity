/*
 * SENTINEL Shield - Canary Token Detection
 * 
 * Detect and track canary tokens for data exfiltration protection
 */

#ifndef SHIELD_CANARY_H
#define SHIELD_CANARY_H

#include "shield_common.h"

/* Canary token types */
typedef enum canary_type {
    CANARY_TYPE_STRING,     /* Plain text marker */
    CANARY_TYPE_TOKEN = CANARY_TYPE_STRING, /* Alias for TOKEN */
    CANARY_TYPE_UUID,       /* UUID format */
    CANARY_TYPE_EMAIL,      /* Email address */
    CANARY_TYPE_URL,        /* URL */
    CANARY_TYPE_HASH,       /* Hash value */
    CANARY_TYPE_CUSTOM,     /* Custom pattern */
} canary_type_t;

/* Canary token */
typedef struct canary_token {
    char            id[64];
    canary_type_t   type;
    char            value[256];
    char            description[128];
    uint64_t        created_at;
    uint64_t        triggered_count;
    char            last_triggered_by[64];
    uint64_t        last_triggered_at;
    struct canary_token *next;
} canary_token_t;

/* Canary manager */
typedef struct canary_manager {
    canary_token_t  *tokens;
    uint32_t        count;
    bool            alert_enabled;
    void            (*alert_callback)(const canary_token_t *token, const char *context);
} canary_manager_t;

/* Canary detection result */
typedef struct canary_result {
    bool            detected;
    canary_token_t  *token;
    size_t          position;
    char            context[256];
} canary_result_t;

/* API */
shield_err_t canary_manager_init(canary_manager_t *mgr);
void canary_manager_destroy(canary_manager_t *mgr);

shield_err_t canary_create(canary_manager_t *mgr, canary_type_t type,
                            const char *value, const char *description,
                            canary_token_t **out);
shield_err_t canary_delete(canary_manager_t *mgr, const char *id);
canary_token_t *canary_find(canary_manager_t *mgr, const char *id);

/* Detection */
canary_result_t canary_scan(canary_manager_t *mgr, const char *text, size_t len);
bool canary_contains_any(canary_manager_t *mgr, const char *text, size_t len);

/* Generate random canary */
shield_err_t canary_generate(canary_manager_t *mgr, canary_type_t type,
                              canary_token_t **out);

/* Alert callback */
void canary_set_alert_callback(canary_manager_t *mgr,
                                void (*callback)(const canary_token_t *, const char *));

/* Load/Save */
shield_err_t canary_load(canary_manager_t *mgr, const char *filename);
shield_err_t canary_save(canary_manager_t *mgr, const char *filename);

#endif /* SHIELD_CANARY_H */
