/*
 * SENTINEL Shield - Zone Registry Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_zone.h"

/* Initialize zone registry */
shield_err_t zone_registry_init(zone_registry_t *reg)
{
    if (!reg) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(reg, 0, sizeof(*reg));
    reg->next_id = 1;
    
    return SHIELD_OK;
}

/* Destroy zone registry */
void zone_registry_destroy(zone_registry_t *reg)
{
    if (!reg) {
        return;
    }
    
    shield_zone_t *zone = reg->zones;
    while (zone) {
        shield_zone_t *next = zone->next;
        free(zone);
        zone = next;
    }
    
    reg->zones = NULL;
    reg->count = 0;
}

/* Create a new zone */
shield_err_t zone_create(zone_registry_t *reg, const char *name,
                         zone_type_t type, shield_zone_t **out)
{
    if (!reg || !name || strlen(name) == 0) {
        return SHIELD_ERR_INVALID;
    }
    
    if (reg->count >= SHIELD_MAX_ZONES) {
        return SHIELD_ERR_FULL;
    }
    
    /* Check if zone already exists */
    if (zone_find_by_name(reg, name)) {
        return SHIELD_ERR_EXISTS;
    }
    
    /* Allocate zone */
    shield_zone_t *zone = calloc(1, sizeof(shield_zone_t));
    if (!zone) {
        return SHIELD_ERR_NOMEM;
    }
    
    zone->id = reg->next_id++;
    strncpy(zone->name, name, SHIELD_MAX_NAME_LEN - 1);
    zone->type = type;
    zone->enabled = true;
    zone->timeout_ms = 5000;
    zone->rate_limit = 100;
    zone->priority = 50;
    
    /* Add to list */
    zone->next = reg->zones;
    reg->zones = zone;
    reg->count++;
    
    if (out) {
        *out = zone;
    }
    
    return SHIELD_OK;
}

/* Delete a zone */
shield_err_t zone_delete(zone_registry_t *reg, const char *name)
{
    if (!reg || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    shield_zone_t **pp = &reg->zones;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            shield_zone_t *zone = *pp;
            *pp = zone->next;
            free(zone);
            reg->count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Find zone by name */
shield_zone_t *zone_find_by_name(zone_registry_t *reg, const char *name)
{
    if (!reg || !name) {
        return NULL;
    }
    
    shield_zone_t *zone = reg->zones;
    while (zone) {
        if (strcmp(zone->name, name) == 0) {
            return zone;
        }
        zone = zone->next;
    }
    
    return NULL;
}

/* Find zone by ID */
shield_zone_t *zone_find_by_id(zone_registry_t *reg, uint32_t id)
{
    if (!reg) {
        return NULL;
    }
    
    shield_zone_t *zone = reg->zones;
    while (zone) {
        if (zone->id == id) {
            return zone;
        }
        zone = zone->next;
    }
    
    return NULL;
}

/* Set provider */
shield_err_t zone_set_provider(shield_zone_t *zone, const char *provider)
{
    if (!zone || !provider) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(zone->provider, provider, SHIELD_MAX_NAME_LEN - 1);
    return SHIELD_OK;
}

/* Set description */
shield_err_t zone_set_description(shield_zone_t *zone, const char *desc)
{
    if (!zone || !desc) {
        return SHIELD_ERR_INVALID;
    }
    
    strncpy(zone->description, desc, SHIELD_MAX_DESC_LEN - 1);
    return SHIELD_OK;
}

/* Set enabled */
shield_err_t zone_set_enabled(shield_zone_t *zone, bool enabled)
{
    if (!zone) {
        return SHIELD_ERR_INVALID;
    }
    
    zone->enabled = enabled;
    return SHIELD_OK;
}

/* Set ACLs */
shield_err_t zone_set_acl(shield_zone_t *zone, uint32_t in_acl, uint32_t out_acl)
{
    if (!zone) {
        return SHIELD_ERR_INVALID;
    }
    
    zone->in_acl = in_acl;
    zone->out_acl = out_acl;
    return SHIELD_OK;
}

/* Iterate zones */
void zone_foreach(zone_registry_t *reg, zone_callback_t cb, void *ctx)
{
    if (!reg || !cb) {
        return;
    }
    
    shield_zone_t *zone = reg->zones;
    while (zone) {
        cb(zone, ctx);
        zone = zone->next;
    }
}

/* Update statistics */
void zone_increment_stats(shield_zone_t *zone, rule_direction_t dir,
                          bool blocked)
{
    if (!zone) {
        return;
    }
    
    if (dir == DIRECTION_INPUT) {
        zone->requests_in++;
        if (blocked) {
            zone->blocked_in++;
        }
    } else if (dir == DIRECTION_OUTPUT) {
        zone->requests_out++;
        if (blocked) {
            zone->blocked_out++;
        }
    }
}

/* Reset statistics */
void zone_reset_stats(shield_zone_t *zone)
{
    if (!zone) {
        return;
    }
    
    zone->requests_in = 0;
    zone->requests_out = 0;
    zone->blocked_in = 0;
    zone->blocked_out = 0;
}
