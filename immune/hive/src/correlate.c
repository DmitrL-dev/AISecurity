/*
 * SENTINEL IMMUNE — Hive Correlation Engine
 * 
 * XDR cross-agent event correlation for detecting:
 * - Lateral movement
 * - Data exfiltration
 * - Coordinated attacks
 * - Attack chains
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

#include "../include/hive.h"

/* ==================== Configuration ==================== */

#define CORRELATION_WINDOW_SEC  300     /* 5 minute window */
#define MAX_CORRELATED_EVENTS   64
#define MAX_ATTACK_CHAINS       16
#define LATERAL_THRESHOLD       3       /* Same sig on N agents = lateral */
#define EXFIL_PORT_THRESHOLD    5       /* N connections to same port = exfil */

/* ==================== Structures ==================== */

typedef struct {
    uint64_t        event_ids[MAX_CORRELATED_EVENTS];
    uint32_t        agent_ids[MAX_CORRELATED_EVENTS];
    int             event_count;
    float           confidence;
    char            attack_type[64];
    time_t          first_seen;
    time_t          last_seen;
} correlation_t;

typedef struct {
    char            name[64];
    char            stages[8][64];
    int             stage_count;
    response_action_t response;
} attack_chain_t;

/* Known attack chains (MITRE ATT&CK inspired) */
static attack_chain_t known_chains[] = {
    {
        .name = "Reverse Shell Attack",
        .stages = {"exec_from_tmp", "network_4444", "priv_escalation"},
        .stage_count = 3,
        .response = RESPONSE_ISOLATE
    },
    {
        .name = "Credential Harvesting",
        .stages = {"open_shadow", "open_ssh_keys", "network_exfil"},
        .stage_count = 3,
        .response = RESPONSE_BLOCK
    },
    {
        .name = "Lateral Movement",
        .stages = {"ssh_connect", "exec_remote", "credential_copy"},
        .stage_count = 3,
        .response = RESPONSE_ISOLATE
    },
    { .name = "" } /* Sentinel */
};

/* ==================== State ==================== */

static correlation_t    g_correlations[MAX_ATTACK_CHAINS];
static int              g_correlation_count = 0;
static pthread_mutex_t  g_corr_lock = PTHREAD_MUTEX_INITIALIZER;

/* ==================== Helpers ==================== */

static int
signature_matches(const char *sig, const char *pattern)
{
    return strstr(sig, pattern) != NULL;
}

static int
count_events_by_signature(immune_hive_t *hive, const char *sig_pattern,
                          time_t window_sec, uint32_t *agents, int max_agents)
{
    time_t now = time(NULL);
    int count = 0;
    int unique_agents = 0;
    
    pthread_mutex_lock(&hive->threats_lock);
    
    for (int i = 0; i < hive->threat_count && count < max_agents; i++) {
        threat_event_t *event = &hive->threats[i];
        
        if (now - event->timestamp > window_sec)
            continue;
        
        if (signature_matches(event->signature, sig_pattern)) {
            /* Check if agent already counted */
            int found = 0;
            for (int j = 0; j < unique_agents; j++) {
                if (agents[j] == event->agent_id) {
                    found = 1;
                    break;
                }
            }
            if (!found && unique_agents < max_agents) {
                agents[unique_agents++] = event->agent_id;
            }
            count++;
        }
    }
    
    pthread_mutex_unlock(&hive->threats_lock);
    
    return unique_agents;
}

/* ==================== Detection Functions ==================== */

int
correlate_detect_lateral_movement(immune_hive_t *hive)
{
    uint32_t agents[32];
    int detected = 0;
    
    /* Check for same execution patterns across multiple hosts */
    const char *lateral_sigs[] = {
        "/tmp/", "bash -i", "nc ", "reverse", "ssh",
        NULL
    };
    
    for (int i = 0; lateral_sigs[i] != NULL; i++) {
        int agent_count = count_events_by_signature(
            hive, lateral_sigs[i], CORRELATION_WINDOW_SEC, agents, 32);
        
        if (agent_count >= LATERAL_THRESHOLD) {
            printf("[CORRELATE] LATERAL MOVEMENT: '%s' on %d agents!\n",
                   lateral_sigs[i], agent_count);
            
            /* Create correlation record */
            pthread_mutex_lock(&g_corr_lock);
            
            if (g_correlation_count < MAX_ATTACK_CHAINS) {
                correlation_t *corr = &g_correlations[g_correlation_count++];
                memset(corr, 0, sizeof(*corr));
                
                strncpy(corr->attack_type, "Lateral Movement", 
                        sizeof(corr->attack_type) - 1);
                corr->event_count = agent_count;
                memcpy(corr->agent_ids, agents, agent_count * sizeof(uint32_t));
                corr->confidence = 0.85f;
                corr->first_seen = time(NULL);
                corr->last_seen = time(NULL);
            }
            
            pthread_mutex_unlock(&g_corr_lock);
            detected++;
        }
    }
    
    return detected;
}

int
correlate_detect_exfiltration(immune_hive_t *hive)
{
    /* Check for multiple connections to same external port */
    uint32_t port_counts[65536] = {0};
    int detected = 0;
    time_t now = time(NULL);
    
    pthread_mutex_lock(&hive->threats_lock);
    
    for (int i = 0; i < hive->threat_count; i++) {
        threat_event_t *event = &hive->threats[i];
        
        if (now - event->timestamp > CORRELATION_WINDOW_SEC)
            continue;
        
        /* Parse port from signature like "connect 1.2.3.4:4444" */
        char *port_str = strrchr(event->signature, ':');
        if (port_str) {
            int port = atoi(port_str + 1);
            if (port > 0 && port < 65536)
                port_counts[port]++;
        }
    }
    
    pthread_mutex_unlock(&hive->threats_lock);
    
    /* Check for suspicious port patterns */
    for (int port = 1; port < 65536; port++) {
        if (port_counts[port] >= EXFIL_PORT_THRESHOLD) {
            printf("[CORRELATE] DATA EXFIL: %d connections to port %d!\n",
                   port_counts[port], port);
            detected++;
        }
    }
    
    return detected;
}

int
correlate_detect_attack_chain(immune_hive_t *hive)
{
    time_t now = time(NULL);
    int detected = 0;
    
    /* For each known attack chain */
    for (int c = 0; known_chains[c].name[0] != '\0'; c++) {
        attack_chain_t *chain = &known_chains[c];
        int stages_found = 0;
        
        pthread_mutex_lock(&hive->threats_lock);
        
        /* Check if all stages present in window */
        for (int s = 0; s < chain->stage_count; s++) {
            for (int i = 0; i < hive->threat_count; i++) {
                threat_event_t *event = &hive->threats[i];
                
                if (now - event->timestamp > CORRELATION_WINDOW_SEC)
                    continue;
                
                if (signature_matches(event->signature, chain->stages[s])) {
                    stages_found++;
                    break;
                }
            }
        }
        
        pthread_mutex_unlock(&hive->threats_lock);
        
        if (stages_found == chain->stage_count) {
            printf("[CORRELATE] ATTACK CHAIN: '%s' detected! (%d stages)\n",
                   chain->name, chain->stage_count);
            detected++;
        }
    }
    
    return detected;
}

/* ==================== Main Correlation Loop ==================== */

int
correlate_analyze(immune_hive_t *hive)
{
    int total = 0;
    
    total += correlate_detect_lateral_movement(hive);
    total += correlate_detect_exfiltration(hive);
    total += correlate_detect_attack_chain(hive);
    
    if (total > 0) {
        printf("[CORRELATE] Analysis complete: %d correlated threats\n", total);
    }
    
    return total;
}

void*
correlate_thread(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    
    printf("[CORRELATE] Correlation engine started\n");
    
    while (hive->running) {
        sleep(30); /* Run every 30 seconds */
        correlate_analyze(hive);
    }
    
    printf("[CORRELATE] Correlation engine stopped\n");
    return NULL;
}

int
correlate_get_results(correlation_t *results, int max_results)
{
    int count;
    
    pthread_mutex_lock(&g_corr_lock);
    count = g_correlation_count < max_results ? g_correlation_count : max_results;
    memcpy(results, g_correlations, count * sizeof(correlation_t));
    pthread_mutex_unlock(&g_corr_lock);
    
    return count;
}

void
correlate_clear(void)
{
    pthread_mutex_lock(&g_corr_lock);
    g_correlation_count = 0;
    memset(g_correlations, 0, sizeof(g_correlations));
    pthread_mutex_unlock(&g_corr_lock);
}
