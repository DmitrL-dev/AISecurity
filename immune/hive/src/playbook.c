/*
 * SENTINEL IMMUNE — Hive Playbook Engine
 * 
 * Automated response playbooks for MDR automation:
 * - Threat-triggered actions
 * - Multi-step response sequences
 * - HAMMER2 forensic integration
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

#include "../include/hive.h"

/* ==================== Configuration ==================== */

#define MAX_PLAYBOOKS       32
#define MAX_ACTIONS         8
#define MAX_CONDITIONS      4

/* ==================== Structures ==================== */

typedef enum {
    COND_LEVEL_GTE,         /* Threat level >= value */
    COND_TYPE_EQ,           /* Threat type == value */
    COND_SIGNATURE_MATCH,   /* Signature contains pattern */
    COND_AGENT_COUNT_GTE,   /* Affected agents >= value */
    COND_TIME_RANGE         /* Within time range */
} condition_type_t;

typedef struct {
    condition_type_t    type;
    int                 int_value;
    char                str_value[64];
} playbook_condition_t;

typedef struct {
    response_action_t   action;
    int                 delay_sec;
    char                params[128];
} playbook_action_t;

typedef struct {
    char                name[64];
    char                description[256];
    int                 enabled;
    int                 priority;           /* Lower = higher priority */
    playbook_condition_t conditions[MAX_CONDITIONS];
    int                 condition_count;
    playbook_action_t   actions[MAX_ACTIONS];
    int                 action_count;
    uint64_t            executions;
    time_t              last_execution;
} playbook_t;

/* ==================== State ==================== */

static playbook_t       g_playbooks[MAX_PLAYBOOKS];
static int              g_playbook_count = 0;
static pthread_mutex_t  g_playbook_lock = PTHREAD_MUTEX_INITIALIZER;

/* ==================== Built-in Playbooks ==================== */

static void
init_default_playbooks(void)
{
    /* Playbook 1: Critical Threat Response */
    playbook_t *pb = &g_playbooks[0];
    strncpy(pb->name, "Critical Threat Response", sizeof(pb->name) - 1);
    strncpy(pb->description, "Auto-isolate on critical threats", sizeof(pb->description) - 1);
    pb->enabled = 1;
    pb->priority = 1;
    pb->conditions[0].type = COND_LEVEL_GTE;
    pb->conditions[0].int_value = THREAT_LEVEL_CRITICAL;
    pb->condition_count = 1;
    pb->actions[0].action = RESPONSE_ALERT;
    pb->actions[0].delay_sec = 0;
    pb->actions[1].action = RESPONSE_ISOLATE;
    pb->actions[1].delay_sec = 5;
    pb->action_count = 2;
    
    /* Playbook 2: Reverse Shell Detection */
    pb = &g_playbooks[1];
    strncpy(pb->name, "Reverse Shell Detection", sizeof(pb->name) - 1);
    strncpy(pb->description, "Block and alert on reverse shell patterns", sizeof(pb->description) - 1);
    pb->enabled = 1;
    pb->priority = 2;
    pb->conditions[0].type = COND_SIGNATURE_MATCH;
    strncpy(pb->conditions[0].str_value, "4444", sizeof(pb->conditions[0].str_value) - 1);
    pb->condition_count = 1;
    pb->actions[0].action = RESPONSE_BLOCK;
    pb->actions[0].delay_sec = 0;
    pb->actions[1].action = RESPONSE_ALERT;
    pb->actions[1].delay_sec = 0;
    strncpy(pb->actions[1].params, "HAMMER2_SNAPSHOT", sizeof(pb->actions[1].params) - 1);
    pb->action_count = 2;
    
    /* Playbook 3: Credential Access */
    pb = &g_playbooks[2];
    strncpy(pb->name, "Credential Access", sizeof(pb->name) - 1);
    strncpy(pb->description, "Alert on sensitive file access", sizeof(pb->description) - 1);
    pb->enabled = 1;
    pb->priority = 3;
    pb->conditions[0].type = COND_SIGNATURE_MATCH;
    strncpy(pb->conditions[0].str_value, "shadow", sizeof(pb->conditions[0].str_value) - 1);
    pb->conditions[1].type = COND_SIGNATURE_MATCH;
    strncpy(pb->conditions[1].str_value, "ssh", sizeof(pb->conditions[1].str_value) - 1);
    pb->condition_count = 2;
    pb->actions[0].action = RESPONSE_ALERT;
    pb->actions[0].delay_sec = 0;
    pb->action_count = 1;
    
    /* Playbook 4: Lateral Movement */
    pb = &g_playbooks[3];
    strncpy(pb->name, "Lateral Movement Response", sizeof(pb->name) - 1);
    strncpy(pb->description, "Isolate hosts in lateral movement chain", sizeof(pb->description) - 1);
    pb->enabled = 1;
    pb->priority = 1;
    pb->conditions[0].type = COND_AGENT_COUNT_GTE;
    pb->conditions[0].int_value = 3;
    pb->condition_count = 1;
    pb->actions[0].action = RESPONSE_ISOLATE;
    pb->actions[0].delay_sec = 0;
    strncpy(pb->actions[0].params, "ALL_AFFECTED_HOSTS", sizeof(pb->actions[0].params) - 1);
    pb->action_count = 1;
    
    g_playbook_count = 4;
}

/* ==================== Condition Matching ==================== */

static int
condition_matches(playbook_condition_t *cond, threat_event_t *event)
{
    switch (cond->type) {
    case COND_LEVEL_GTE:
        return event->level >= cond->int_value;
        
    case COND_TYPE_EQ:
        return event->type == cond->int_value;
        
    case COND_SIGNATURE_MATCH:
        return strstr(event->signature, cond->str_value) != NULL ||
               strstr(event->source_file, cond->str_value) != NULL;
        
    case COND_AGENT_COUNT_GTE:
        /* Would check correlation data */
        return 0;
        
    case COND_TIME_RANGE:
        /* Check if within configured hours */
        return 1;
        
    default:
        return 0;
    }
}

static int
playbook_matches(playbook_t *pb, threat_event_t *event)
{
    if (!pb->enabled)
        return 0;
    
    /* All conditions must match (AND logic) */
    for (int i = 0; i < pb->condition_count; i++) {
        if (!condition_matches(&pb->conditions[i], event))
            return 0;
    }
    
    return 1;
}

/* ==================== Action Execution ==================== */

static int
execute_action(immune_hive_t *hive, playbook_action_t *action, 
               threat_event_t *event)
{
    printf("[PLAYBOOK] Execute action: %d (delay=%ds)\n",
           action->action, action->delay_sec);
    
    if (action->delay_sec > 0)
        sleep(action->delay_sec);
    
    /* Check for special params */
    if (strcmp(action->params, "HAMMER2_SNAPSHOT") == 0) {
        printf("[PLAYBOOK] Triggering HAMMER2 forensic snapshot\n");
        /* Would call hammer2_snapshot() */
    }
    
    /* Execute the response action */
    event->action = action->action;
    /* Would call response handler */
    printf("[PLAYBOOK] Response action %d executed\n", action->action);
    return 0;
}

/* ==================== Public API ==================== */

int
playbook_init(void)
{
    pthread_mutex_lock(&g_playbook_lock);
    init_default_playbooks();
    pthread_mutex_unlock(&g_playbook_lock);
    
    printf("[PLAYBOOK] Engine initialized with %d playbooks\n", g_playbook_count);
    return 0;
}

int
playbook_execute(immune_hive_t *hive, threat_event_t *event)
{
    if (!hive || !event)
        return -1;
    
    int executed = 0;
    
    pthread_mutex_lock(&g_playbook_lock);
    
    /* Find matching playbooks (sorted by priority) */
    for (int i = 0; i < g_playbook_count; i++) {
        playbook_t *pb = &g_playbooks[i];
        
        if (playbook_matches(pb, event)) {
            printf("[PLAYBOOK] Matched: '%s'\n", pb->name);
            
            /* Execute all actions in sequence */
            for (int a = 0; a < pb->action_count; a++) {
                execute_action(hive, &pb->actions[a], event);
            }
            
            pb->executions++;
            pb->last_execution = time(NULL);
            executed++;
            
            /* Only execute highest priority matching playbook */
            break;
        }
    }
    
    pthread_mutex_unlock(&g_playbook_lock);
    
    return executed;
}

int
playbook_add(playbook_t *pb)
{
    pthread_mutex_lock(&g_playbook_lock);
    
    if (g_playbook_count >= MAX_PLAYBOOKS) {
        pthread_mutex_unlock(&g_playbook_lock);
        return -1;
    }
    
    memcpy(&g_playbooks[g_playbook_count], pb, sizeof(playbook_t));
    g_playbook_count++;
    
    pthread_mutex_unlock(&g_playbook_lock);
    
    printf("[PLAYBOOK] Added: '%s'\n", pb->name);
    return 0;
}

int
playbook_list(playbook_t *list, int max_count)
{
    pthread_mutex_lock(&g_playbook_lock);
    
    int count = g_playbook_count < max_count ? g_playbook_count : max_count;
    memcpy(list, g_playbooks, count * sizeof(playbook_t));
    
    pthread_mutex_unlock(&g_playbook_lock);
    return count;
}

void
playbook_stats(void)
{
    pthread_mutex_lock(&g_playbook_lock);
    
    printf("\n=== PLAYBOOK STATISTICS ===\n");
    for (int i = 0; i < g_playbook_count; i++) {
        playbook_t *pb = &g_playbooks[i];
        printf("  %s: %lu executions (enabled=%d)\n",
               pb->name, pb->executions, pb->enabled);
    }
    printf("===========================\n\n");
    
    pthread_mutex_unlock(&g_playbook_lock);
}
