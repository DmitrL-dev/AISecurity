/*
 * SENTINEL Shield - High Availability Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "shield_common.h"
#include "shield_ha.h"
#include "shield_platform.h"
#include "shield_qrng.h"

/* Get current time in ms */
static uint64_t get_time_ms(void)
{
    return platform_time_ms();
}

/* Generate node ID using QRNG */
static void generate_node_id(char *id, size_t len)
{
    const char hex[] = "0123456789abcdef";
    
    for (size_t i = 0; i < len - 1 && i < 16; i++) {
        id[i] = hex[shield_qrng_u32() % 16];
    }
    id[len > 16 ? 16 : len - 1] = '\0';
}

/* Initialize cluster */
shield_err_t ha_cluster_init(ha_cluster_t *cluster, const char *node_id,
                              const char *address, uint16_t port)
{
    if (!cluster || !address) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(cluster, 0, sizeof(*cluster));
    
    /* Local node */
    if (node_id) {
        strncpy(cluster->local.id, node_id, sizeof(cluster->local.id) - 1);
    } else {
        generate_node_id(cluster->local.id, sizeof(cluster->local.id));
    }
    
    strncpy(cluster->local.address, address, sizeof(cluster->local.address) - 1);
    cluster->local.port = port ? port : 5400;
    cluster->local.role = HA_ROLE_STANDALONE;
    cluster->local.state = HA_STATE_INIT;
    cluster->local.priority = 100;
    cluster->local.last_heartbeat = get_time_ms();
    cluster->local.config_version = 1;
    
    /* Peer allocation */
    cluster->max_peers = 4;
    cluster->peers = calloc(cluster->max_peers, sizeof(ha_node_t));
    if (!cluster->peers) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Settings */
    cluster->heartbeat_interval_ms = 1000;
    cluster->failover_timeout_ms = 5000;
    cluster->preemption = false;
    
    cluster->initialized = true;
    
    LOG_INFO("HA cluster initialized: node=%s addr=%s:%u",
             cluster->local.id, cluster->local.address, cluster->local.port);
    
    return SHIELD_OK;
}

/* Destroy cluster */
void ha_cluster_destroy(ha_cluster_t *cluster)
{
    if (!cluster) {
        return;
    }
    
    ha_stop(cluster);
    
    free(cluster->peers);
    cluster->peers = NULL;
    cluster->peer_count = 0;
    cluster->initialized = false;
}

/* Add peer */
shield_err_t ha_add_peer(ha_cluster_t *cluster, const char *address, uint16_t port)
{
    if (!cluster || !address) {
        return SHIELD_ERR_INVALID;
    }
    
    if (cluster->peer_count >= cluster->max_peers) {
        return SHIELD_ERR_NOMEM;
    }
    
    /* Check duplicate */
    for (int i = 0; i < cluster->peer_count; i++) {
        if (strcmp(cluster->peers[i].address, address) == 0 &&
            cluster->peers[i].port == port) {
            return SHIELD_ERR_EXISTS;
        }
    }
    
    ha_node_t *peer = &cluster->peers[cluster->peer_count++];
    generate_node_id(peer->id, sizeof(peer->id));
    strncpy(peer->address, address, sizeof(peer->address) - 1);
    peer->port = port ? port : 5400;
    peer->role = HA_ROLE_STANDBY;
    peer->state = HA_STATE_UNKNOWN;
    peer->priority = 100 + cluster->peer_count;
    
    LOG_INFO("HA: Added peer %s:%u", address, port);
    
    if (cluster->on_peer_change) {
        cluster->on_peer_change(peer, true, cluster->callback_ctx);
    }
    
    return SHIELD_OK;
}

/* Remove peer */
shield_err_t ha_remove_peer(ha_cluster_t *cluster, const char *node_id)
{
    if (!cluster || !node_id) {
        return SHIELD_ERR_INVALID;
    }
    
    for (int i = 0; i < cluster->peer_count; i++) {
        if (strcmp(cluster->peers[i].id, node_id) == 0) {
            ha_node_t removed = cluster->peers[i];
            
            /* Shift remaining */
            for (int j = i; j < cluster->peer_count - 1; j++) {
                cluster->peers[j] = cluster->peers[j + 1];
            }
            cluster->peer_count--;
            
            LOG_INFO("HA: Removed peer %s", node_id);
            
            if (cluster->on_peer_change) {
                cluster->on_peer_change(&removed, false, cluster->callback_ctx);
            }
            
            return SHIELD_OK;
        }
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Start cluster */
shield_err_t ha_start(ha_cluster_t *cluster)
{
    if (!cluster || !cluster->initialized) {
        return SHIELD_ERR_INVALID;
    }
    
    cluster->running = true;
    
    if (cluster->peer_count == 0) {
        /* Standalone mode */
        cluster->local.role = HA_ROLE_STANDALONE;
        cluster->local.state = HA_STATE_ACTIVE;
    } else {
        /* Determine initial role based on priority */
        bool highest_priority = true;
        
        for (int i = 0; i < cluster->peer_count; i++) {
            if (cluster->peers[i].priority < cluster->local.priority) {
                highest_priority = false;
                break;
            }
        }
        
        if (highest_priority) {
            cluster->local.role = HA_ROLE_ACTIVE;
            cluster->local.state = HA_STATE_SYNC;
        } else {
            cluster->local.role = HA_ROLE_STANDBY;
            cluster->local.state = HA_STATE_SYNC;
        }
    }
    
    LOG_INFO("HA: Started as %s",
             cluster->local.role == HA_ROLE_ACTIVE ? "ACTIVE" :
             cluster->local.role == HA_ROLE_STANDBY ? "STANDBY" : "STANDALONE");
    
    return SHIELD_OK;
}

/* Stop cluster */
void ha_stop(ha_cluster_t *cluster)
{
    if (!cluster) {
        return;
    }
    
    cluster->running = false;
    cluster->local.state = HA_STATE_UNKNOWN;
    
    LOG_INFO("HA: Stopped");
}

/* Force active */
shield_err_t ha_force_active(ha_cluster_t *cluster)
{
    if (!cluster) {
        return SHIELD_ERR_INVALID;
    }
    
    ha_role_t old_role = cluster->local.role;
    cluster->local.role = HA_ROLE_ACTIVE;
    cluster->local.state = HA_STATE_ACTIVE;
    
    LOG_INFO("HA: Forced to ACTIVE");
    
    if (cluster->on_role_change && old_role != HA_ROLE_ACTIVE) {
        cluster->on_role_change(old_role, HA_ROLE_ACTIVE, cluster->callback_ctx);
    }
    
    return SHIELD_OK;
}

/* Force standby */
shield_err_t ha_force_standby(ha_cluster_t *cluster)
{
    if (!cluster) {
        return SHIELD_ERR_INVALID;
    }
    
    ha_role_t old_role = cluster->local.role;
    cluster->local.role = HA_ROLE_STANDBY;
    cluster->local.state = HA_STATE_STANDBY;
    
    LOG_INFO("HA: Forced to STANDBY");
    
    if (cluster->on_role_change && old_role != HA_ROLE_STANDBY) {
        cluster->on_role_change(old_role, HA_ROLE_STANDBY, cluster->callback_ctx);
    }
    
    return SHIELD_OK;
}

/* Sync config */
shield_err_t ha_sync_config(ha_cluster_t *cluster)
{
    if (!cluster) {
        return SHIELD_ERR_INVALID;
    }
    
    /* TODO: Implement actual sync via SHSP */
    LOG_DEBUG("HA: Config sync requested (stub)");
    
    cluster->local.config_version++;
    
    return SHIELD_OK;
}

/* Sync blocklist */
shield_err_t ha_sync_blocklist(ha_cluster_t *cluster)
{
    if (!cluster) {
        return SHIELD_ERR_INVALID;
    }
    
    LOG_DEBUG("HA: Blocklist sync requested (stub)");
    return SHIELD_OK;
}

/* Sync sessions */
shield_err_t ha_sync_sessions(ha_cluster_t *cluster)
{
    if (!cluster) {
        return SHIELD_ERR_INVALID;
    }
    
    LOG_DEBUG("HA: Session sync requested (stub)");
    return SHIELD_OK;
}

/* Getters */
ha_role_t ha_get_role(ha_cluster_t *cluster)
{
    return cluster ? cluster->local.role : HA_ROLE_STANDALONE;
}

ha_state_t ha_get_state(ha_cluster_t *cluster)
{
    return cluster ? cluster->local.state : HA_STATE_UNKNOWN;
}

int ha_get_peer_count(ha_cluster_t *cluster)
{
    return cluster ? cluster->peer_count : 0;
}

bool ha_is_active(ha_cluster_t *cluster)
{
    if (!cluster) return true;
    return cluster->local.role == HA_ROLE_ACTIVE ||
           cluster->local.role == HA_ROLE_STANDALONE;
}

/* Set callbacks */
void ha_set_callbacks(ha_cluster_t *cluster,
                       void (*on_role)(ha_role_t, ha_role_t, void *),
                       void (*on_peer)(const ha_node_t *, bool, void *),
                       void *ctx)
{
    if (cluster) {
        cluster->on_role_change = on_role;
        cluster->on_peer_change = on_peer;
        cluster->callback_ctx = ctx;
    }
}
