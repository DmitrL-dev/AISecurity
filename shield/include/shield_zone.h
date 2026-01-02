/*
 * SENTINEL Shield - Zone Registry
 * 
 * Manages untrusted zones (LLMs, RAGs, Agents, Tools, etc.)
 */

#ifndef SHIELD_ZONE_H
#define SHIELD_ZONE_H

#include "shield_common.h"

/* Zone structure */
typedef struct shield_zone {
    uint32_t        id;
    char            name[SHIELD_MAX_NAME_LEN];
    zone_type_t     type;
    char            provider[SHIELD_MAX_NAME_LEN];
    char            description[SHIELD_MAX_DESC_LEN];
    bool            enabled;
    uint32_t        in_acl;     /* Ingress access-list */
    uint32_t        out_acl;    /* Egress access-list */
    
    /* Statistics */
    uint64_t        requests_in;
    uint64_t        requests_out;
    uint64_t        blocked_in;
    uint64_t        blocked_out;
    
    /* Configuration */
    uint32_t        timeout_ms;
    uint32_t        rate_limit;
    uint32_t        priority;
    
    struct shield_zone *next;
} shield_zone_t;

/* Zone registry */
typedef struct zone_registry {
    shield_zone_t   *zones;
    uint32_t        count;
    uint32_t        next_id;
} zone_registry_t;

/* API */
shield_err_t zone_registry_init(zone_registry_t *reg);
void zone_registry_destroy(zone_registry_t *reg);

shield_err_t zone_create(zone_registry_t *reg, const char *name, 
                         zone_type_t type, shield_zone_t **out);
shield_err_t zone_delete(zone_registry_t *reg, const char *name);
shield_zone_t *zone_find_by_name(zone_registry_t *reg, const char *name);
shield_zone_t *zone_find_by_id(zone_registry_t *reg, uint32_t id);

shield_err_t zone_set_provider(shield_zone_t *zone, const char *provider);
shield_err_t zone_set_description(shield_zone_t *zone, const char *desc);
shield_err_t zone_set_enabled(shield_zone_t *zone, bool enabled);
shield_err_t zone_set_acl(shield_zone_t *zone, uint32_t in_acl, uint32_t out_acl);

/* Iteration */
typedef void (*zone_callback_t)(shield_zone_t *zone, void *ctx);
void zone_foreach(zone_registry_t *reg, zone_callback_t cb, void *ctx);

/* Statistics */
void zone_increment_stats(shield_zone_t *zone, rule_direction_t dir, 
                          bool blocked);
void zone_reset_stats(shield_zone_t *zone);

#endif /* SHIELD_ZONE_H */
