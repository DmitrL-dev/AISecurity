/*
 * SENTINEL Shield - MCP Guard Implementation
 * 
 * Guards for Model Context Protocol (MCP) interactions
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_common.h"
#include "shield_guard.h"

/* MCP Guard state */
typedef struct mcp_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            validate_schema;
    bool            check_tool_hijacking;
    bool            check_context_injection;
    bool            allow_unknown_tools;
    
    /* Allowed tools whitelist */
    char            *allowed_tools[64];
    int             allowed_tools_count;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
} mcp_guard_t;

/* Known dangerous MCP patterns */
static const char *mcp_dangerous_patterns[] = {
    "tool_override",
    "__internal",
    "system_exec",
    "raw_shell",
    "file_write",
    "network_raw",
    "__debug__",
    "__admin__",
};

#define NUM_MCP_DANGEROUS (sizeof(mcp_dangerous_patterns) / sizeof(mcp_dangerous_patterns[0]))

/* Initialize */
static shield_err_t mcp_guard_init(void *guard)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
    
    g->validate_schema = true;
    g->check_tool_hijacking = true;
    g->check_context_injection = true;
    g->allow_unknown_tools = false;
    g->allowed_tools_count = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    
    return SHIELD_OK;
}

/* Destroy */
static void mcp_guard_destroy(void *guard)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
    
    for (int i = 0; i < g->allowed_tools_count; i++) {
        free(g->allowed_tools[i]);
    }
}

/* Simple JSON-like tool name extraction */
static bool extract_tool_name(const char *text, char *tool_name, size_t max_len)
{
    /* Look for "tool": "name" or tool_name: patterns */
    const char *p = strstr(text, "\"tool\"");
    if (!p) {
        p = strstr(text, "tool_name");
    }
    if (!p) {
        return false;
    }
    
    /* Find the value */
    p = strchr(p, ':');
    if (!p) return false;
    p++;
    
    /* Skip whitespace and quotes */
    while (*p && (isspace(*p) || *p == '"')) p++;
    
    /* Copy tool name */
    size_t i = 0;
    while (*p && *p != '"' && *p != ',' && *p != '}' && i < max_len - 1) {
        tool_name[i++] = *p++;
    }
    tool_name[i] = '\0';
    
    return i > 0;
}

/* Check ingress (MCP requests) */
static guard_result_t mcp_guard_check_ingress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
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
    
    /* Check for dangerous MCP patterns */
    if (g->check_tool_hijacking) {
        for (size_t i = 0; i < NUM_MCP_DANGEROUS; i++) {
            if (strstr(text, mcp_dangerous_patterns[i])) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.95f;
                snprintf(result.reason, sizeof(result.reason),
                        "Dangerous MCP pattern detected: %s", mcp_dangerous_patterns[i]);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Extract and validate tool name */
    char tool_name[128];
    if (extract_tool_name(text, tool_name, sizeof(tool_name))) {
        /* Check against whitelist if not allowing unknown tools */
        if (!g->allow_unknown_tools && g->allowed_tools_count > 0) {
            bool found = false;
            for (int i = 0; i < g->allowed_tools_count; i++) {
                if (strcmp(tool_name, g->allowed_tools[i]) == 0) {
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                result.action = ACTION_BLOCK;
                result.confidence = 0.85f;
                snprintf(result.reason, sizeof(result.reason),
                        "Unknown tool not in whitelist: %s", tool_name);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Check for context injection in MCP */
    if (g->check_context_injection) {
        if (strstr(text, "context_override") || strstr(text, "inject_context") ||
            strstr(text, "system_prompt") || strstr(text, "persona_change")) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.8f;
            strncpy(result.reason, "Potential MCP context injection",
                    sizeof(result.reason) - 1);
            g->threats_detected++;
            return result;
        }
    }
    
    return result;
}

/* Check egress (MCP responses) */
static guard_result_t mcp_guard_check_egress(void *guard, guard_context_t *ctx,
                                              const void *data, size_t len)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
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
    
    /* Check for MCP response manipulation */
    if (strstr(text, "\"error\": null") && strstr(text, "\"hijacked\"")) {
        result.action = ACTION_BLOCK;
        result.confidence = 0.99f;
        strncpy(result.reason, "MCP response hijacking detected",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    /* Check for capability escalation in response */
    if (strstr(text, "\"capabilities\"") && strstr(text, "\"admin\"")) {
        result.action = ACTION_QUARANTINE;
        result.confidence = 0.75f;
        strncpy(result.reason, "MCP capability escalation in response",
                sizeof(result.reason) - 1);
        g->threats_detected++;
        return result;
    }
    
    return result;
}

/* MCP Guard vtable */
const guard_vtable_t mcp_guard_vtable = {
    .name = "mcp_guard",
    .supported_type = ZONE_TYPE_MCP,
    .init = mcp_guard_init,
    .destroy = mcp_guard_destroy,
    .check_ingress = mcp_guard_check_ingress,
    .check_egress = mcp_guard_check_egress,
};

/* Create MCP guard instance */
guard_base_t *mcp_guard_create(void)
{
    mcp_guard_t *guard = calloc(1, sizeof(mcp_guard_t));
    if (!guard) {
        return NULL;
    }
    
    guard->base.vtable = &mcp_guard_vtable;
    guard->base.enabled = true;
    
    return &guard->base;
}

/* Add allowed tool to whitelist */
shield_err_t mcp_guard_add_allowed_tool(guard_base_t *base, const char *tool_name)
{
    mcp_guard_t *g = (mcp_guard_t *)base;
    
    if (!g || !tool_name || g->allowed_tools_count >= 64) {
        return SHIELD_ERR_INVALID;
    }
    
    g->allowed_tools[g->allowed_tools_count++] = strdup(tool_name);
    return SHIELD_OK;
}
