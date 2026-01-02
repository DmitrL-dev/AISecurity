/*
 * SENTINEL Shield - Guard Registry Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* Initialize guard registry */
shield_err_t guard_registry_init(guard_registry_t *reg)
{
    if (!reg) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(reg, 0, sizeof(*reg));
    return SHIELD_OK;
}

/* Destroy guard registry */
void guard_registry_destroy(guard_registry_t *reg)
{
    if (!reg) {
        return;
    }
    
    for (uint32_t i = 0; i < reg->count; i++) {
        guard_base_t *guard = reg->guards[i];
        if (guard && guard->vtable && guard->vtable->destroy) {
            guard->vtable->destroy(guard);
        }
    }
    
    reg->count = 0;
}

/* Register guard */
shield_err_t guard_register(guard_registry_t *reg, guard_base_t *guard)
{
    if (!reg || !guard || !guard->vtable) {
        return SHIELD_ERR_INVALID;
    }
    
    if (reg->count >= SHIELD_MAX_GUARDS) {
        return SHIELD_ERR_FULL;
    }
    
    /* Initialize guard */
    if (guard->vtable->init) {
        shield_err_t err = guard->vtable->init(guard);
        if (err != SHIELD_OK) {
            return err;
        }
    }
    
    reg->guards[reg->count++] = guard;
    return SHIELD_OK;
}

/* Find guard by type */
guard_base_t *guard_find_by_type(guard_registry_t *reg, zone_type_t type)
{
    if (!reg) {
        return NULL;
    }
    
    for (uint32_t i = 0; i < reg->count; i++) {
        guard_base_t *guard = reg->guards[i];
        if (guard && guard->vtable && 
            guard->vtable->supported_type == type) {
            return guard;
        }
    }
    
    return NULL;
}

/* Find guard by name */
guard_base_t *guard_find_by_name(guard_registry_t *reg, const char *name)
{
    if (!reg || !name) {
        return NULL;
    }
    
    for (uint32_t i = 0; i < reg->count; i++) {
        guard_base_t *guard = reg->guards[i];
        if (guard && guard->vtable && guard->vtable->name &&
            strcmp(guard->vtable->name, name) == 0) {
            return guard;
        }
    }
    
    return NULL;
}

/* Evaluate with guards */
guard_result_t guard_evaluate(guard_registry_t *reg, guard_context_t *ctx,
                               const void *data, size_t len)
{
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    if (!reg || !ctx || !data || len == 0) {
        return result;
    }
    
    /* Find appropriate guard */
    guard_base_t *guard = guard_find_by_type(reg, ctx->zone->type);
    if (!guard || !guard->enabled) {
        return result;
    }
    
    /* Evaluate based on direction */
    if (ctx->direction == DIRECTION_INPUT) {
        if (guard->vtable->check_ingress) {
            result = guard->vtable->check_ingress(guard, ctx, data, len);
        }
    } else if (ctx->direction == DIRECTION_OUTPUT) {
        if (guard->vtable->check_egress) {
            result = guard->vtable->check_egress(guard, ctx, data, len);
        }
    }
    
    return result;
}
