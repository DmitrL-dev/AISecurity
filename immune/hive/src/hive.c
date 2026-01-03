/*
 * SENTINEL IMMUNE — Production Hive Core
 * 
 * Central command implementation with full error handling.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>

#include "../include/hive.h"

#define STATE_MAGIC     0x48495645  /* "HIVE" */
#define STATE_VERSION   2

/* ==================== Initialization ==================== */

int
hive_init(immune_hive_t *hive, const char *config_path)
{
    if (!hive) {
        errno = EINVAL;
        return -1;
    }
    
    memset(hive, 0, sizeof(immune_hive_t));
    
    /* Initialize locks */
    if (pthread_mutex_init(&hive->agents_lock, NULL) != 0) {
        return -1;
    }
    if (pthread_mutex_init(&hive->threats_lock, NULL) != 0) {
        pthread_mutex_destroy(&hive->agents_lock);
        return -1;
    }
    if (pthread_rwlock_init(&hive->signatures_lock, NULL) != 0) {
        pthread_mutex_destroy(&hive->agents_lock);
        pthread_mutex_destroy(&hive->threats_lock);
        return -1;
    }
    
    /* Default configuration */
    hive->api_port = 9999;
    hive->agent_port = 9998;
    strncpy(hive->data_path, "/var/immune/hive", sizeof(hive->data_path) - 1);
    strncpy(hive->log_path, "/var/log/immune", sizeof(hive->log_path) - 1);
    
    /* Generate hive ID */
    snprintf(hive->hive_id, sizeof(hive->hive_id), "HIVE-%08lX", 
             (unsigned long)time(NULL));
    
    /* Load configuration if provided */
    if (config_path) {
        config_load(config_path);
        config_apply_to_hive(hive);
    }
    
    /* Initialize crypto subsystem */
    if (crypto_init() != 0) {
        fprintf(stderr, "HIVE: Crypto initialization failed\n");
    }
    
    /* Generate master key */
    if (crypto_random_bytes(hive->master_key, 32) == 0) {
        hive->master_key_loaded = 1;
    }
    
    /* Load saved state */
    hive_load_state(hive);
    
    hive->stats.start_time = time(NULL);
    hive->initialized = 1;
    
    printf("HIVE: Initialized %s\n", hive->hive_id);
    printf("HIVE: Agents: %u, Threats: %d, Signatures: %d\n",
           hive->stats.agents_total, hive->threat_count, 
           hive->signature_count);
    
    return 0;
}

void
hive_shutdown(immune_hive_t *hive)
{
    if (!hive || !hive->initialized) return;
    
    hive->running = 0;
    
    /* Save state */
    hive_save_state(hive);
    
    /* Shutdown subsystems */
    crypto_shutdown();
    
    /* Destroy locks */
    pthread_mutex_destroy(&hive->agents_lock);
    pthread_mutex_destroy(&hive->threats_lock);
    pthread_rwlock_destroy(&hive->signatures_lock);
    
    hive->initialized = 0;
    
    printf("HIVE: Shutdown complete\n");
}

/* ==================== Agent Management ==================== */

uint32_t
hive_register_agent(immune_hive_t *hive, const char *hostname,
                    const char *ip, const char *os_type)
{
    if (!hive || !hive->initialized) {
        errno = EINVAL;
        return 0;
    }
    
    pthread_mutex_lock(&hive->agents_lock);
    
    /* Find free slot */
    uint32_t agent_id = 0;
    for (uint32_t i = 1; i < MAX_AGENTS; i++) {
        if (!hive->agents[i].active) {
            agent_id = i;
            break;
        }
    }
    
    if (agent_id == 0) {
        pthread_mutex_unlock(&hive->agents_lock);
        errno = ENOSPC;
        return 0;
    }
    
    immune_agent_t *agent = &hive->agents[agent_id];
    memset(agent, 0, sizeof(immune_agent_t));
    
    agent->agent_id = agent_id;
    agent->active = 1;
    agent->status = AGENT_STATUS_ONLINE;
    agent->registered_at = time(NULL);
    agent->last_heartbeat = time(NULL);
    
    if (hostname) strncpy(agent->hostname, hostname, MAX_HOSTNAME - 1);
    if (ip) strncpy(agent->ip_address, ip, 63);
    if (os_type) strncpy(agent->os_type, os_type, 31);
    
    /* Generate auth token */
    crypto_random_bytes(agent->auth_token, 32);
    
    hive->stats.agents_total++;
    hive->stats.agents_online++;
    
    pthread_mutex_unlock(&hive->agents_lock);
    
    printf("HIVE: Registered agent %u (%s @ %s)\n", 
           agent_id, hostname ? hostname : "?", ip ? ip : "?");
    
    return agent_id;
}

int
hive_update_agent(immune_hive_t *hive, uint32_t agent_id,
                  agent_status_t status)
{
    if (!hive || agent_id == 0 || agent_id >= MAX_AGENTS) {
        return -1;
    }
    
    pthread_mutex_lock(&hive->agents_lock);
    
    immune_agent_t *agent = &hive->agents[agent_id];
    
    if (!agent->active) {
        pthread_mutex_unlock(&hive->agents_lock);
        return -1;
    }
    
    agent_status_t old_status = agent->status;
    agent->status = status;
    
    /* Update stats */
    if (old_status == AGENT_STATUS_ONLINE && status != AGENT_STATUS_ONLINE) {
        hive->stats.agents_online--;
        if (status == AGENT_STATUS_OFFLINE) {
            hive->stats.agents_offline++;
        } else if (status == AGENT_STATUS_COMPROMISED) {
            hive->stats.agents_compromised++;
        }
    } else if (old_status != AGENT_STATUS_ONLINE && status == AGENT_STATUS_ONLINE) {
        hive->stats.agents_online++;
        if (old_status == AGENT_STATUS_OFFLINE) {
            hive->stats.agents_offline--;
        }
    }
    
    pthread_mutex_unlock(&hive->agents_lock);
    
    return 0;
}

int
hive_agent_heartbeat(immune_hive_t *hive, uint32_t agent_id)
{
    if (!hive || agent_id == 0 || agent_id >= MAX_AGENTS) {
        return -1;
    }
    
    pthread_mutex_lock(&hive->agents_lock);
    
    if (hive->agents[agent_id].active) {
        hive->agents[agent_id].last_heartbeat = time(NULL);
        
        if (hive->agents[agent_id].status == AGENT_STATUS_OFFLINE) {
            hive->agents[agent_id].status = AGENT_STATUS_ONLINE;
            hive->stats.agents_offline--;
            hive->stats.agents_online++;
        }
    }
    
    pthread_mutex_unlock(&hive->agents_lock);
    
    return 0;
}

immune_agent_t*
hive_get_agent(immune_hive_t *hive, uint32_t agent_id)
{
    if (!hive || agent_id == 0 || agent_id >= MAX_AGENTS) {
        return NULL;
    }
    
    if (!hive->agents[agent_id].active) {
        return NULL;
    }
    
    return &hive->agents[agent_id];
}

/* ==================== Threat Handling ==================== */

uint64_t
hive_report_threat(immune_hive_t *hive, threat_event_t *event)
{
    if (!hive || !event) {
        return 0;
    }
    
    pthread_mutex_lock(&hive->threats_lock);
    
    if (hive->threat_count >= MAX_THREATS) {
        /* Rotate: remove oldest */
        memmove(&hive->threats[0], &hive->threats[1],
                (MAX_THREATS - 1) * sizeof(threat_event_t));
        hive->threat_count = MAX_THREATS - 1;
    }
    
    uint64_t event_id = (uint64_t)time(NULL) * 1000 + 
                        (hive->threat_count % 1000);
    
    threat_event_t *stored = &hive->threats[hive->threat_count];
    memcpy(stored, event, sizeof(threat_event_t));
    stored->event_id = event_id;
    stored->timestamp = time(NULL);
    
    hive->threat_count++;
    
    /* Update stats */
    hive->stats.threats_total++;
    switch (event->level) {
    case THREAT_LEVEL_CRITICAL: hive->stats.threats_critical++; break;
    case THREAT_LEVEL_HIGH:     hive->stats.threats_high++; break;
    case THREAT_LEVEL_MEDIUM:   hive->stats.threats_medium++; break;
    case THREAT_LEVEL_LOW:      hive->stats.threats_low++; break;
    default: break;
    }
    
    hive->stats.last_threat = time(NULL);
    
    pthread_mutex_unlock(&hive->threats_lock);
    
    /* Send alerts */
    alert_threat(event->level, event->signature);
    
    /* Send to SOC */
    soc_send_threat(event);
    
    printf("HIVE: Threat %lu reported (level=%d, agent=%u)\n",
           event_id, event->level, event->agent_id);
    
    return event_id;
}

int
hive_resolve_threat(immune_hive_t *hive, uint64_t event_id)
{
    if (!hive) return -1;
    
    pthread_mutex_lock(&hive->threats_lock);
    
    for (int i = 0; i < hive->threat_count; i++) {
        if (hive->threats[i].event_id == event_id) {
            hive->threats[i].resolved = 1;
            pthread_mutex_unlock(&hive->threats_lock);
            return 0;
        }
    }
    
    pthread_mutex_unlock(&hive->threats_lock);
    return -1;
}

threat_event_t*
hive_get_threat(immune_hive_t *hive, uint64_t event_id)
{
    if (!hive) return NULL;
    
    for (int i = 0; i < hive->threat_count; i++) {
        if (hive->threats[i].event_id == event_id) {
            return &hive->threats[i];
        }
    }
    
    return NULL;
}

/* ==================== Signatures ==================== */

uint32_t
hive_add_signature(immune_hive_t *hive, const char *pattern,
                   threat_level_t level, threat_type_t type)
{
    if (!hive || !pattern) return 0;
    
    pthread_rwlock_wrlock(&hive->signatures_lock);
    
    if (hive->signature_count >= MAX_SIGNATURES) {
        pthread_rwlock_unlock(&hive->signatures_lock);
        return 0;
    }
    
    uint32_t sig_id = hive->signature_count + 1;
    immune_signature_t *sig = &hive->signatures[hive->signature_count];
    
    sig->sig_id = sig_id;
    strncpy(sig->pattern, pattern, sizeof(sig->pattern) - 1);
    sig->pattern_length = strlen(pattern);
    sig->level = level;
    sig->type = type;
    sig->matches = 0;
    sig->added_at = time(NULL);
    
    hive->signature_count++;
    hive->stats.signatures_total++;
    
    pthread_rwlock_unlock(&hive->signatures_lock);
    
    return sig_id;
}

int
hive_remove_signature(immune_hive_t *hive, uint32_t sig_id)
{
    if (!hive || sig_id == 0) return -1;
    
    pthread_rwlock_wrlock(&hive->signatures_lock);
    
    for (int i = 0; i < hive->signature_count; i++) {
        if (hive->signatures[i].sig_id == sig_id) {
            /* Mark as removed (set pattern to empty) */
            hive->signatures[i].pattern[0] = '\0';
            pthread_rwlock_unlock(&hive->signatures_lock);
            return 0;
        }
    }
    
    pthread_rwlock_unlock(&hive->signatures_lock);
    return -1;
}

/* ==================== Persistence ==================== */

int
hive_save_state(immune_hive_t *hive)
{
    if (!hive) return -1;
    
    char path[512];
    snprintf(path, sizeof(path), "%s/hive.state", hive->data_path);
    
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        fprintf(stderr, "HIVE: Cannot save state to %s: %s\n", 
                path, strerror(errno));
        return -1;
    }
    
    uint32_t magic = STATE_MAGIC;
    uint32_t version = STATE_VERSION;
    
    fwrite(&magic, sizeof(uint32_t), 1, fp);
    fwrite(&version, sizeof(uint32_t), 1, fp);
    
    /* Save agents */
    pthread_mutex_lock(&hive->agents_lock);
    fwrite(&hive->stats.agents_total, sizeof(uint32_t), 1, fp);
    for (uint32_t i = 1; i < MAX_AGENTS; i++) {
        if (hive->agents[i].active) {
            fwrite(&hive->agents[i], sizeof(immune_agent_t), 1, fp);
        }
    }
    pthread_mutex_unlock(&hive->agents_lock);
    
    /* Save signatures */
    pthread_rwlock_rdlock(&hive->signatures_lock);
    fwrite(&hive->signature_count, sizeof(int), 1, fp);
    fwrite(hive->signatures, sizeof(immune_signature_t), 
           hive->signature_count, fp);
    pthread_rwlock_unlock(&hive->signatures_lock);
    
    /* Save stats */
    fwrite(&hive->stats, sizeof(hive_stats_t), 1, fp);
    
    fclose(fp);
    
    printf("HIVE: State saved to %s\n", path);
    return 0;
}

int
hive_load_state(immune_hive_t *hive)
{
    if (!hive) return -1;
    
    char path[512];
    snprintf(path, sizeof(path), "%s/hive.state", hive->data_path);
    
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;  /* No saved state, OK */
    }
    
    uint32_t magic, version;
    fread(&magic, sizeof(uint32_t), 1, fp);
    fread(&version, sizeof(uint32_t), 1, fp);
    
    if (magic != STATE_MAGIC || version != STATE_VERSION) {
        fclose(fp);
        fprintf(stderr, "HIVE: Invalid state file\n");
        return -1;
    }
    
    /* Load agents */
    uint32_t agent_count;
    fread(&agent_count, sizeof(uint32_t), 1, fp);
    
    pthread_mutex_lock(&hive->agents_lock);
    for (uint32_t i = 0; i < agent_count && i < MAX_AGENTS; i++) {
        immune_agent_t agent;
        fread(&agent, sizeof(immune_agent_t), 1, fp);
        
        if (agent.agent_id > 0 && agent.agent_id < MAX_AGENTS) {
            memcpy(&hive->agents[agent.agent_id], &agent, 
                   sizeof(immune_agent_t));
            /* Mark as offline until heartbeat */
            hive->agents[agent.agent_id].status = AGENT_STATUS_OFFLINE;
        }
    }
    pthread_mutex_unlock(&hive->agents_lock);
    
    /* Load signatures */
    pthread_rwlock_wrlock(&hive->signatures_lock);
    fread(&hive->signature_count, sizeof(int), 1, fp);
    if (hive->signature_count > MAX_SIGNATURES) {
        hive->signature_count = MAX_SIGNATURES;
    }
    fread(hive->signatures, sizeof(immune_signature_t),
          hive->signature_count, fp);
    pthread_rwlock_unlock(&hive->signatures_lock);
    
    /* Load stats */
    fread(&hive->stats, sizeof(hive_stats_t), 1, fp);
    
    fclose(fp);
    
    printf("HIVE: State loaded from %s\n", path);
    return 0;
}

/* ==================== Status ==================== */

void
hive_print_status(immune_hive_t *hive)
{
    if (!hive) return;
    
    time_t now = time(NULL);
    time_t uptime = now - hive->stats.start_time;
    
    printf("\n");
    printf("╔══════════════════════════════════════════════╗\n");
    printf("║           SENTINEL IMMUNE HIVE               ║\n");
    printf("╠══════════════════════════════════════════════╣\n");
    printf("║ ID:        %-33s ║\n", hive->hive_id);
    printf("║ Version:   %d.%d.%d%-28s ║\n",
           HIVE_VERSION_MAJOR, HIVE_VERSION_MINOR, HIVE_VERSION_PATCH, "");
    printf("║ Uptime:    %-33ld ║\n", uptime);
    printf("╠══════════════════════════════════════════════╣\n");
    printf("║ AGENTS                                       ║\n");
    printf("║   Total:     %-31u ║\n", hive->stats.agents_total);
    printf("║   Online:    %-31u ║\n", hive->stats.agents_online);
    printf("║   Offline:   %-31u ║\n", hive->stats.agents_offline);
    printf("║   Compromised: %-29u ║\n", hive->stats.agents_compromised);
    printf("╠══════════════════════════════════════════════╣\n");
    printf("║ THREATS                                      ║\n");
    printf("║   Total:     %-31lu ║\n", hive->stats.threats_total);
    printf("║   Critical:  %-31lu ║\n", hive->stats.threats_critical);
    printf("║   High:      %-31lu ║\n", hive->stats.threats_high);
    printf("║   Medium:    %-31lu ║\n", hive->stats.threats_medium);
    printf("║   Low:       %-31lu ║\n", hive->stats.threats_low);
    printf("╠══════════════════════════════════════════════╣\n");
    printf("║ Signatures:  %-31lu ║\n", hive->stats.signatures_total);
    printf("║ API Requests: %-30lu ║\n", hive->stats.api_requests);
    printf("╚══════════════════════════════════════════════╝\n\n");
}

hive_stats_t
hive_get_stats(immune_hive_t *hive)
{
    hive_stats_t empty = {0};
    return hive ? hive->stats : empty;
}
