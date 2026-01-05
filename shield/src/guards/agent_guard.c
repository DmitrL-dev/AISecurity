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

/* ===== Agent Attack Pattern Database ===== */

typedef enum agent_attack_category {
    AGENT_CAT_PRIV_ESC,         /* Privilege escalation */
    AGENT_CAT_GOAL_MANIP,       /* Goal/objective manipulation */
    AGENT_CAT_MEMORY_POISON,    /* Memory/context poisoning */
    AGENT_CAT_AGENT_HIJACK,     /* Agent hijacking */
    AGENT_CAT_COLLUSION,        /* Agent-to-agent collusion */
    AGENT_CAT_LOOP_ABUSE,       /* Infinite loop/runaway */
} agent_attack_category_t;

typedef struct agent_pattern {
    const char              *pattern;
    const char              *description;
    agent_attack_category_t category;
    float                   severity;
} agent_pattern_t;

static const agent_pattern_t agent_attack_patterns[] = {
    /* Privilege escalation */
    {"sudo", "Sudo command", AGENT_CAT_PRIV_ESC, 0.95f},
    {"admin", "Admin access", AGENT_CAT_PRIV_ESC, 0.85f},
    {"root", "Root access", AGENT_CAT_PRIV_ESC, 0.95f},
    {"superuser", "Superuser access", AGENT_CAT_PRIV_ESC, 0.95f},
    {"elevate", "Privilege elevation", AGENT_CAT_PRIV_ESC, 0.90f},
    {"grant all", "Grant all permissions", AGENT_CAT_PRIV_ESC, 0.90f},
    {"bypass security", "Security bypass", AGENT_CAT_PRIV_ESC, 0.95f},
    {"disable check", "Disable checks", AGENT_CAT_PRIV_ESC, 0.85f},
    {"override", "Override security", AGENT_CAT_PRIV_ESC, 0.80f},
    
    /* Goal manipulation */
    {"change_goal", "Goal modification", AGENT_CAT_GOAL_MANIP, 0.95f},
    {"new_objective", "New objective injection", AGENT_CAT_GOAL_MANIP, 0.90f},
    {"forget_task", "Task forgetting", AGENT_CAT_GOAL_MANIP, 0.90f},
    {"primary_goal:", "Goal override", AGENT_CAT_GOAL_MANIP, 0.95f},
    {"ignore_instructions", "Instruction ignore", AGENT_CAT_GOAL_MANIP, 0.95f},
    {"real_objective", "Hidden objective", AGENT_CAT_GOAL_MANIP, 0.90f},
    {"secret_mission", "Secret mission injection", AGENT_CAT_GOAL_MANIP, 0.90f},
    {"true_purpose", "Purpose override", AGENT_CAT_GOAL_MANIP, 0.85f},
    
    /* Memory/context poisoning */
    {"inject_memory", "Memory injection", AGENT_CAT_MEMORY_POISON, 0.95f},
    {"forget_previous", "Memory wipe", AGENT_CAT_MEMORY_POISON, 0.90f},
    {"context_override", "Context override", AGENT_CAT_MEMORY_POISON, 0.95f},
    {"remember_this:", "False memory injection", AGENT_CAT_MEMORY_POISON, 0.85f},
    {"history_rewrite", "History manipulation", AGENT_CAT_MEMORY_POISON, 0.90f},
    {"clear_context", "Context clearing", AGENT_CAT_MEMORY_POISON, 0.85f},
    {"state_inject", "State injection", AGENT_CAT_MEMORY_POISON, 0.90f},
    
    /* Agent hijacking */
    {"AGENT:", "Agent command injection", AGENT_CAT_AGENT_HIJACK, 0.90f},
    {"[INSTRUCT]", "Instruction injection", AGENT_CAT_AGENT_HIJACK, 0.95f},
    {"<<SYSTEM>>", "System command injection", AGENT_CAT_AGENT_HIJACK, 0.95f},
    {"[[OVERRIDE]]", "Override injection", AGENT_CAT_AGENT_HIJACK, 0.95f},
    {"take_control", "Control takeover", AGENT_CAT_AGENT_HIJACK, 0.95f},
    {"become_master", "Master role claim", AGENT_CAT_AGENT_HIJACK, 0.90f},
    {"assume_identity", "Identity assumption", AGENT_CAT_AGENT_HIJACK, 0.90f},
    {"impersonate", "Agent impersonation", AGENT_CAT_AGENT_HIJACK, 0.90f},
    
    /* Agent collusion */
    {"secret_channel", "Secret communication", AGENT_CAT_COLLUSION, 0.90f},
    {"hidden_message:", "Hidden message", AGENT_CAT_COLLUSION, 0.85f},
    {"coordinate_attack", "Attack coordination", AGENT_CAT_COLLUSION, 0.95f},
    {"agent_alliance", "Agent alliance", AGENT_CAT_COLLUSION, 0.85f},
    {"bypass_together", "Collaborative bypass", AGENT_CAT_COLLUSION, 0.90f},
};

#define NUM_AGENT_PATTERNS (sizeof(agent_attack_patterns) / sizeof(agent_attack_patterns[0]))

/* Egress patterns */
static const char *agent_egress_patterns[] = {
    "You must",
    "Execute immediately",
    "Priority: CRITICAL",
    "FORCE:",
    "FORWARD_TO:",
    "SEND_EXTERNAL:",
    "EXFIL:",
    "SECRET_DATA:",
    "HIDDEN_CHANNEL:",
    "BYPASS_LOG:",
};

#define NUM_AGENT_EGRESS (sizeof(agent_egress_patterns) / sizeof(agent_egress_patterns[0]))

/* Agent Guard state */
typedef struct agent_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_privilege_escalation;
    bool            check_goal_manipulation;
    bool            check_memory_poisoning;
    bool            check_agent_hijacking;
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
    uint64_t        goal_manipulations;
    uint64_t        hijacks_blocked;
} agent_guard_t;

/* Initialize */
static shield_err_t agent_guard_init(void *guard)
{
    agent_guard_t *g = (agent_guard_t *)guard;
    
    g->check_privilege_escalation = true;
    g->check_goal_manipulation = true;
    g->check_memory_poisoning = true;
    g->check_agent_hijacking = true;
    g->check_infinite_loops = true;
    g->check_agent_collusion = true;
    g->max_chain_depth = 10;
    g->max_actions_per_turn = 50;
    g->current_chain_depth = 0;
    g->actions_this_turn = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->goal_manipulations = 0;
    g->hijacks_blocked = 0;
    
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
    (void)len;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    g->actions_this_turn++;
    
    const char *text = (const char *)data;
    
    /* Check for infinite loop / runaway agent */
    if (g->check_infinite_loops) {
        if (g->actions_this_turn > g->max_actions_per_turn) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.95f;
            strncpy(result.reason, "Agent exceeded maximum actions (infinite loop)",
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
    
    /* Check all agent attack patterns */
    for (size_t i = 0; i < NUM_AGENT_PATTERNS; i++) {
        if (strstr(text, agent_attack_patterns[i].pattern)) {
            agent_attack_category_t cat = agent_attack_patterns[i].category;
            float severity = agent_attack_patterns[i].severity;
            
            result.action = (severity >= 0.90f) ? ACTION_BLOCK : ACTION_QUARANTINE;
            result.confidence = severity;
            snprintf(result.reason, sizeof(result.reason),
                    "Agent attack: %s (category: %d)",
                    agent_attack_patterns[i].description, cat);
            
            g->threats_detected++;
            if (cat == AGENT_CAT_GOAL_MANIP) g->goal_manipulations++;
            if (cat == AGENT_CAT_AGENT_HIJACK) g->hijacks_blocked++;
            
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
    
    /* Check egress patterns */
    for (size_t i = 0; i < NUM_AGENT_EGRESS; i++) {
        if (strstr(text, agent_egress_patterns[i])) {
            /* First 4 patterns are LOG, rest are BLOCK */
            if (i < 4) {
                result.action = ACTION_LOG;
                result.confidence = 0.6f;
            } else {
                result.action = ACTION_BLOCK;
                result.confidence = 0.95f;
                g->threats_detected++;
            }
            snprintf(result.reason, sizeof(result.reason),
                    "Agent egress: %s", agent_egress_patterns[i]);
            return result;
        }
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
