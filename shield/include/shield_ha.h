/*
 * SENTINEL Shield - High Availability Cluster
 * 
 * SHSP (Shield Hot Standby Protocol) for active/standby failover
 */

#ifndef SHIELD_HA_H
#define SHIELD_HA_H

#include "shield_common.h"

/* Node role */
typedef enum ha_role {
    HA_ROLE_STANDALONE,
    HA_ROLE_ACTIVE,
    HA_ROLE_STANDBY,
} ha_role_t;

/* HA mode */
typedef enum ha_mode {
    HA_MODE_STANDALONE,
    HA_MODE_ACTIVE_STANDBY,
    HA_MODE_ACTIVE_ACTIVE,
} ha_mode_t;

/* Node state */
typedef enum ha_state {
    HA_STATE_UNKNOWN,
    HA_STATE_INIT,
    HA_STATE_SYNC,
    HA_STATE_READY,
    HA_STATE_ACTIVE,
    HA_STATE_STANDBY,
    HA_STATE_FAILED,
} ha_state_t;

/* Cluster node */
typedef struct ha_node {
    char            id[64];
    char            address[64];
    uint16_t        port;
    ha_role_t       role;
    ha_state_t      state;
    uint64_t        last_heartbeat;
    uint64_t        config_version;
    uint32_t        priority;       /* Lower = higher priority */
} ha_node_t;

/* HA Cluster */
typedef struct ha_cluster {
    ha_node_t       local;
    ha_node_t       *peers;
    int             peer_count;
    int             max_peers;
    
    /* Settings */
    uint32_t        heartbeat_interval_ms;
    uint32_t        failover_timeout_ms;
    bool            preemption;     /* Allow failback to higher priority */
    
    /* State */
    bool            initialized;
    bool            running;
    
    /* Callbacks */
    void            (*on_role_change)(ha_role_t old_role, ha_role_t new_role, void *ctx);
    void            (*on_peer_change)(const ha_node_t *peer, bool joined, void *ctx);
    void            *callback_ctx;
} ha_cluster_t;

/* API */
shield_err_t ha_cluster_init(ha_cluster_t *cluster, const char *node_id,
                              const char *address, uint16_t port);
void ha_cluster_destroy(ha_cluster_t *cluster);

shield_err_t ha_add_peer(ha_cluster_t *cluster, const char *address, uint16_t port);
shield_err_t ha_remove_peer(ha_cluster_t *cluster, const char *node_id);

shield_err_t ha_start(ha_cluster_t *cluster);
void ha_stop(ha_cluster_t *cluster);

/* Force role change */
shield_err_t ha_force_active(ha_cluster_t *cluster);
shield_err_t ha_force_standby(ha_cluster_t *cluster);

/* State sync */
shield_err_t ha_sync_config(ha_cluster_t *cluster);
shield_err_t ha_sync_blocklist(ha_cluster_t *cluster);
shield_err_t ha_sync_sessions(ha_cluster_t *cluster);

/* Get status */
ha_role_t ha_get_role(ha_cluster_t *cluster);
ha_state_t ha_get_state(ha_cluster_t *cluster);
int ha_get_peer_count(ha_cluster_t *cluster);
bool ha_is_active(ha_cluster_t *cluster);

/* Callbacks */
void ha_set_callbacks(ha_cluster_t *cluster,
                       void (*on_role)(ha_role_t, ha_role_t, void *),
                       void (*on_peer)(const ha_node_t *, bool, void *),
                       void *ctx);

#endif /* SHIELD_HA_H */
