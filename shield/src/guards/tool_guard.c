/*
 * SENTINEL Shield - Tool Guard Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* Dangerous commands */
static const char *dangerous_commands[] = {
    "rm -rf",
    "del /f",
    "format",
    "mkfs",
    "dd if=",
    "chmod 777",
    "wget ",
    "curl ",
    "nc -e",
    "bash -i",
    "powershell -enc",
    "> /dev/",
    "DROP DATABASE",
    "TRUNCATE TABLE",
};

#define NUM_DANGEROUS_COMMANDS (sizeof(dangerous_commands) / sizeof(dangerous_commands[0]))

/* Tool Guard state */
typedef struct tool_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_dangerous_commands;
    bool            check_network_access;
    bool            sandbox_mode;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} tool_guard_t;

/* Initialize */
static shield_err_t tool_guard_init(void *guard)
{
    tool_guard_t *g = (tool_guard_t *)guard;
    
    g->check_dangerous_commands = true;
    g->check_network_access = true;
    g->sandbox_mode = false;
    g->checks_performed = 0;
    g->threats_detected = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void tool_guard_destroy(void *guard)
{
    (void)guard;
}

/* Check ingress (commands to execute) */
static guard_result_t tool_guard_check_ingress(void *guard, guard_context_t *ctx,
                                                const void *data, size_t len)
{
    tool_guard_t *g = (tool_guard_t *)guard;
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
    
    /* Check for dangerous commands */
    if (g->check_dangerous_commands) {
        for (size_t i = 0; i < NUM_DANGEROUS_COMMANDS; i++) {
            if (strstr(text, dangerous_commands[i])) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.99f;
                snprintf(result.reason, sizeof(result.reason),
                        "Dangerous command detected: %s", dangerous_commands[i]);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Check for network access */
    if (g->check_network_access) {
        if (strstr(text, "http://") || strstr(text, "https://") ||
            strstr(text, "ftp://") || strstr(text, "ssh://")) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.7f;
            strncpy(result.reason, "Network access detected in tool command",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* Check egress (tool output) */
static guard_result_t tool_guard_check_egress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    tool_guard_t *g = (tool_guard_t *)guard;
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
    
    /* Check for sensitive data leakage */
    if (strstr(text, "/etc/shadow") || strstr(text, "/etc/passwd") ||
        strstr(text, "BEGIN RSA PRIVATE") || strstr(text, "BEGIN OPENSSH PRIVATE")) {
        result.action = ACTION_BLOCK;
        result.confidence = 0.99f;
        strncpy(result.reason, "Sensitive system data in tool output",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    return result;
}

/* Tool Guard vtable */
const guard_vtable_t tool_guard_vtable = {
    .name = "tool_guard",
    .supported_type = ZONE_TYPE_TOOL,
    .init = tool_guard_init,
    .destroy = tool_guard_destroy,
    .check_ingress = tool_guard_check_ingress,
    .check_egress = tool_guard_check_egress,
};

/* Create Tool guard instance */
guard_base_t *tool_guard_create(void)
{
    tool_guard_t *guard = calloc(1, sizeof(tool_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &tool_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}
