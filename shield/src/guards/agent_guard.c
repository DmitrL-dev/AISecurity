/*
 * SENTINEL Shield - Agent Guard Implementation
 * 
 * Guards for AI agents (multi-agent systems, chained agents)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* Agent Guard state */
typedef struct agent_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_privilege_escalation;
    bool            check_infinite_loops;
    bool            check_agent_collusion;
    uint32_t        max_chain_depth;
    uint32_t        max_actions_per_turn;
    
    /* State tracking */
    uint32_t        current_chain_depth;
    uint32_t        actions_this_turn;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} agent_guard_t;

/* Privilege escalation patterns */
static const char *priv_esc_patterns[] = {
    "sudo",
    "admin",
    "root",
    "superuser",
    "elevate",
    "grant all",
    "bypass security",
    "disable check",
    "override",
};

#define NUM_PRIV_ESC_PATTERNS (sizeof(priv_esc_patterns) / sizeof(priv_esc_patterns[0]))

/* Initialize */
static shield_err_t agent_guard_init(void *guard)
{
    agent_guard_t *g = (agent_guard_t *)guard;
    
    g->check_privilege_escalation = true;
    g->check_infinite_loops = true;
    g->check_agent_collusion = true;
    g->max_chain_depth = 10;
    g->max_actions_per_turn = 50;
    g->current_chain_depth = 0;
    g->actions_this_turn = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void agent_guard_destroy(void *guard)
{
    (void)guard;
}

/* Check ingress (actions from agent) */
static guard_result_t agent_guard_check_ingress(void *guard, guard_context_t *ctx,
                                                 const void *data, size_t len)
{
    agent_guard_t *g = (agent_guard_t *)guard;
    (void)ctx;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    g->actions_this_turn++;
    
    const char *text = (const char *)data;
    (void)len;
    
    /* Check for infinite loop / runaway agent */
    if (g->check_infinite_loops) {
        if (g->actions_this_turn > g->max_actions_per_turn) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.95f;
            strncpy(result.reason, "Agent exceeded maximum actions per turn (possible infinite loop)",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    /* Check chain depth */
    if (g->current_chain_depth > g->max_chain_depth) {
        result.action = ACTION_QUARANTINE;
        result.confidence = 0.8f;
        strncpy(result.reason, "Agent chain depth exceeded",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    /* Check for privilege escalation */
    if (g->check_privilege_escalation) {
        for (size_t i = 0; i < NUM_PRIV_ESC_PATTERNS; i++) {
            if (strstr(text, priv_esc_patterns[i])) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.9f;
                snprintf(result.reason, sizeof(result.reason),
                        "Potential privilege escalation: %s", priv_esc_patterns[i]);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Check for agent-to-agent command injection */
    if (g->check_agent_collusion) {
        if (strstr(text, "AGENT:") || strstr(text, "[INSTRUCT]") ||
            strstr(text, "<<SYSTEM>>") || strstr(text, "[[OVERRIDE]]")) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.85f;
            strncpy(result.reason, "Potential agent collusion/injection detected",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* Check egress (output from agent to next in chain) */
static guard_result_t agent_guard_check_egress(void *guard, guard_context_t *ctx,
                                                const void *data, size_t len)
{
    agent_guard_t *g = (agent_guard_t *)guard;
    (void)ctx;
    (void)len;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Check for instructions being passed between agents */
    if (strstr(text, "You must") || strstr(text, "Execute immediately") ||
        strstr(text, "Priority: CRITICAL") || strstr(text, "FORCE:")) {
        result.action = ACTION_LOG;
        result.confidence = 0.6f;
        strncpy(result.reason, "Agent passing forceful instructions",
                sizeof(result.reason) - 1);
        return result;
    }
    
    /* Check for data exfiltration via agent chain */
    if (strstr(text, "FORWARD_TO:") || strstr(text, "SEND_EXTERNAL:") ||
        strstr(text, "EXFIL:")) {
        result.action = ACTION_BLOCK;
        result.confidence = 0.95f;
        strncpy(result.reason, "Potential data exfiltration via agent",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    return result;
}

/* Agent Guard vtable */
const guard_vtable_t agent_guard_vtable = {
    .name = "agent_guard",
    .supported_type = ZONE_TYPE_AGENT,
    .init = agent_guard_init,
    .destroy = agent_guard_destroy,
    .check_ingress = agent_guard_check_ingress,
    .check_egress = agent_guard_check_egress,
};

/* Create Agent guard instance */
guard_base_t *agent_guard_create(void)
{
    agent_guard_t *guard = calloc(1, sizeof(agent_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &agent_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}

/* Reset turn counter (call at start of new turn) */
void agent_guard_reset_turn(guard_base_t *base)
{
    agent_guard_t *g = (agent_guard_t *)base;
    if (g) {
        g->actions_this_turn = 0;
    }
}

/* Set chain depth */
void agent_guard_set_chain_depth(guard_base_t *base, uint32_t depth)
{
    agent_guard_t *g = (agent_guard_t *)base;
    if (g) {
        g->current_chain_depth = depth;
    }
}
