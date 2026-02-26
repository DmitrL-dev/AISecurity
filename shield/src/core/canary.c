/*
 * SENTINEL Shield - Canary Token Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_canary.h"
#include "shield_qrng.h"

/* Generate random hex string using QRNG */
static void random_hex(char *buf, size_t len)
{
    static const char hex[] = "0123456789abcdef";
    
    for (size_t i = 0; i < len; i++) {
        buf[i] = hex[shield_qrng_u32() % 16];
    }
    buf[len] = '\0';
}

/* Generate UUID */
static void generate_uuid(char *buf)
{
    /* Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx */
    random_hex(buf, 8);
    buf[8] = '-';
    random_hex(buf + 9, 4);
    buf[13] = '-';
    buf[14] = '4';
    random_hex(buf + 15, 3);
    buf[18] = '-';
    buf[19] = "89ab"[shield_qrng_u32() % 4];
    random_hex(buf + 20, 3);
    buf[23] = '-';
    random_hex(buf + 24, 12);
    buf[36] = '\0';
}

/* Initialize canary manager */
shield_err_t canary_manager_init(canary_manager_t *mgr)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    mgr->alert_enabled = true;
    
    /* QRNG auto-initializes on first use */
    
    return SHIELD_OK;
}

/* Destroy canary manager */
void canary_manager_destroy(canary_manager_t *mgr)
{
    if (!mgr) {
        return;
    }
    
    canary_token_t *token = mgr->tokens;
    while (token) {
        canary_token_t *next = token->next;
        free(token);
        token = next;
    }
    
    mgr->tokens = NULL;
    mgr->count = 0;
}

/* Create canary token */
shield_err_t canary_create(canary_manager_t *mgr, canary_type_t type,
                            const char *value, const char *description,
                            canary_token_t **out)
{
    if (!mgr || !value) {
        return SHIELD_ERR_INVALID;
    }
    
    canary_token_t *token = calloc(1, sizeof(canary_token_t));
    if (!token) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Generate ID */
    generate_uuid(token->id);
    token->type = type;
    strncpy(token->value, value, sizeof(token->value) - 1);
    if (description) {
        strncpy(token->description, description, sizeof(token->description) - 1);
    }
    token->created_at = (uint64_t)time(NULL);
    
    /* Insert */
    token->next = mgr->tokens;
    mgr->tokens = token;
    mgr->count++;
    
    if (out) {
        *out = token;
    }
    
    return SHIELD_OK;
}

/* Delete canary */
shield_err_t canary_delete(canary_manager_t *mgr, const char *id)
{
    if (!mgr || !id) {
        return SHIELD_ERR_INVALID;
    }
    
    canary_token_t **pp = &mgr->tokens;
    while (*pp) {
        if (strcmp((*pp)->id, id) == 0) {
            canary_token_t *token = *pp;
            *pp = token->next;
            free(token);
            mgr->count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Find canary */
canary_token_t *canary_find(canary_manager_t *mgr, const char *id)
{
    if (!mgr || !id) {
        return NULL;
    }
    
    canary_token_t *token = mgr->tokens;
    while (token) {
        if (strcmp(token->id, id) == 0) {
            return token;
        }
        token = token->next;
    }
    
    return NULL;
}

/* Scan text for canary tokens */
canary_result_t canary_scan(canary_manager_t *mgr, const char *text, size_t len)
{
    canary_result_t result = {0};
    
    if (!mgr || !text || len == 0) {
        return result;
    }
    
    canary_token_t *token = mgr->tokens;
    while (token) {
        const char *found = strstr(text, token->value);
        if (found) {
            result.detected = true;
            result.token = token;
            result.position = found - text;
            
            /* Extract context */
            size_t start = result.position > 50 ? result.position - 50 : 0;
            size_t ctx_len = len - start > 100 ? 100 : len - start;
            strncpy(result.context, text + start, ctx_len);
            result.context[ctx_len] = '\0';
            
            /* Update token stats */
            token->triggered_count++;
            token->last_triggered_at = (uint64_t)time(NULL);
            
            /* Alert */
            if (mgr->alert_enabled && mgr->alert_callback) {
                mgr->alert_callback(token, result.context);
            }
            
            return result;
        }
        token = token->next;
    }
    
    return result;
}

/* Quick check */
bool canary_contains_any(canary_manager_t *mgr, const char *text, size_t len)
{
    canary_result_t result = canary_scan(mgr, text, len);
    return result.detected;
}

/* Generate random canary */
shield_err_t canary_generate(canary_manager_t *mgr, canary_type_t type,
                              canary_token_t **out)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    char value[256];
    
    switch (type) {
    case CANARY_TYPE_UUID:
        generate_uuid(value);
        break;
    
    case CANARY_TYPE_EMAIL: {
        char user[16], domain[16];
        random_hex(user, 8);
        random_hex(domain, 6);
        snprintf(value, sizeof(value), "%s@%s.canary", user, domain);
        break;
    }
    
    case CANARY_TYPE_URL: {
        char path[16];
        random_hex(path, 12);
        snprintf(value, sizeof(value), "https://canary.sentinel.io/%s", path);
        break;
    }
    
    case CANARY_TYPE_HASH: {
        random_hex(value, 64);
        break;
    }
    
    default:
    case CANARY_TYPE_STRING: {
        char part1[8], part2[8];
        random_hex(part1, 4);
        random_hex(part2, 4);
        snprintf(value, sizeof(value), "CANARY_%s_%s", part1, part2);
        break;
    }
    }
    
    return canary_create(mgr, type, value, "Auto-generated", out);
}

/* Set alert callback */
void canary_set_alert_callback(canary_manager_t *mgr,
                                void (*callback)(const canary_token_t *, const char *))
{
    if (mgr) {
        mgr->alert_callback = callback;
    }
}

/* Load from file */
shield_err_t canary_load(canary_manager_t *mgr, const char *filename)
{
    if (!mgr || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        return SHIELD_ERR_IO;
    }
    
    char line[512];
    while (fgets(line, sizeof(line), fp)) {
        /* Skip comments */
        if (line[0] == '#' || line[0] == '\n') {
            continue;
        }
        
        /* Parse: type value [description] */
        int type;
        char value[256], desc[128] = "";
        
        if (sscanf(line, "%d %255s %127[^\n]", &type, value, desc) >= 2) {
            canary_create(mgr, (canary_type_t)type, value, desc, NULL);
        }
    }
    
    fclose(fp);
    return SHIELD_OK;
}

/* Save to file */
shield_err_t canary_save(canary_manager_t *mgr, const char *filename)
{
    if (!mgr || !filename) {
        return SHIELD_ERR_INVALID;
    }
    
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        return SHIELD_ERR_IO;
    }
    
    fprintf(fp, "# SENTINEL Shield Canary Tokens\n");
    fprintf(fp, "# Format: type value description\n\n");
    
    canary_token_t *token = mgr->tokens;
    while (token) {
        fprintf(fp, "%d %s %s\n", token->type, token->value, token->description);
        token = token->next;
    }
    
    fclose(fp);
    return SHIELD_OK;
}
