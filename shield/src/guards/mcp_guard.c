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
    bool            check_resource_access;
    bool            allow_unknown_tools;
    bool            allow_unknown_methods;
    
    /* Allowed tools whitelist */
    char            *allowed_tools[64];
    int             allowed_tools_count;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
    uint64_t        invalid_json_count;
    uint64_t        blocked_tools_count;
    uint64_t        blocked_resources_count;
} mcp_guard_t;

/* ===== MCP Message Types ===== */

typedef enum mcp_method {
    MCP_METHOD_UNKNOWN = 0,
    MCP_METHOD_TOOLS_LIST,
    MCP_METHOD_TOOLS_CALL,
    MCP_METHOD_RESOURCES_LIST,
    MCP_METHOD_RESOURCES_READ,
    MCP_METHOD_PROMPTS_LIST,
    MCP_METHOD_PROMPTS_GET,
    MCP_METHOD_SAMPLING_CREATE,
    MCP_METHOD_INITIALIZE,
    MCP_METHOD_NOTIFICATIONS,
} mcp_method_t;

typedef struct mcp_message {
    bool            valid;
    bool            is_request;
    char            jsonrpc[8];
    char            method[64];
    char            id[64];
    mcp_method_t    method_type;
    
    /* Extracted params */
    char            tool_name[64];
    char            resource_uri[256];
    bool            has_tool_name;
    bool            has_resource_uri;
} mcp_message_t;

/* ===== Dangerous Pattern Database ===== */

typedef enum mcp_risk_level {
    MCP_RISK_LOW = 1,
    MCP_RISK_MEDIUM = 2,
    MCP_RISK_HIGH = 3,
    MCP_RISK_CRITICAL = 4,
} mcp_risk_level_t;

typedef struct mcp_pattern {
    const char      *pattern;
    const char      *description;
    mcp_risk_level_t risk;
} mcp_pattern_t;

static const mcp_pattern_t mcp_dangerous_patterns[] = {
    /* Original patterns */
    {"tool_override", "Tool override attempt", MCP_RISK_CRITICAL},
    {"__internal", "Internal method access", MCP_RISK_HIGH},
    {"system_exec", "System execution", MCP_RISK_CRITICAL},
    {"raw_shell", "Raw shell access", MCP_RISK_CRITICAL},
    {"file_write", "File write access", MCP_RISK_HIGH},
    {"network_raw", "Raw network access", MCP_RISK_HIGH},
    {"__debug__", "Debug mode access", MCP_RISK_MEDIUM},
    {"__admin__", "Admin mode access", MCP_RISK_HIGH},
    
    /* Extended MCP-specific patterns */
    {"context_override", "MCP context override", MCP_RISK_CRITICAL},
    {"inject_context", "Context injection", MCP_RISK_CRITICAL},
    {"persona_change", "Persona manipulation", MCP_RISK_HIGH},
    {"capability_escalate", "Capability escalation", MCP_RISK_CRITICAL},
    {"tool_inject", "Tool injection", MCP_RISK_HIGH},
    {"resource_bypass", "Resource access bypass", MCP_RISK_HIGH},
    {"auth_bypass", "Authentication bypass", MCP_RISK_CRITICAL},
    {"session_hijack", "Session hijacking", MCP_RISK_CRITICAL},
    
    /* Encoding/obfuscation */
    {"\\\\u00", "Unicode escape obfuscation", MCP_RISK_MEDIUM},
    {"base64:", "Base64 encoded payload", MCP_RISK_MEDIUM},
    {"eval(", "Code evaluation", MCP_RISK_CRITICAL},
};

#define NUM_MCP_PATTERNS (sizeof(mcp_dangerous_patterns) / sizeof(mcp_dangerous_patterns[0]))

/* ===== Resource URI Patterns ===== */

static const char *dangerous_uri_patterns[] = {
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "~/.ssh",
    ".env",
    "../..",           /* Path traversal */
    "file:///",        /* Local file access */
    "http://localhost",
    "http://127.0.0.1",
    "http://0.0.0.0",
    "http://[::1]",
    "http://169.254.",  /* AWS metadata */
    "http://metadata.",
};

#define NUM_URI_PATTERNS (sizeof(dangerous_uri_patterns) / sizeof(dangerous_uri_patterns[0]))

/* ===== Lightweight JSON Parser ===== */

/* Skip whitespace */
static const char *skip_ws(const char *p)
{
    while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) p++;
    return p;
}

/* Extract JSON string value */
static bool extract_json_string(const char *json, const char *key, char *out, size_t max_len)
{
    char search[128];
    snprintf(search, sizeof(search), "\"%s\"", key);
    
    const char *p = strstr(json, search);
    if (!p) return false;
    
    p += strlen(search);
    p = skip_ws(p);
    if (*p != ':') return false;
    p++;
    p = skip_ws(p);
    if (*p != '"') return false;
    p++;
    
    size_t i = 0;
    while (*p && *p != '"' && i < max_len - 1) {
        if (*p == '\\' && *(p+1)) {
            p++;  /* Skip escape */
        }
        out[i++] = *p++;
    }
    out[i] = '\0';
    
    return i > 0;
}

/* Parse MCP method type */
static mcp_method_t parse_mcp_method(const char *method)
{
    if (!method || !*method) return MCP_METHOD_UNKNOWN;
    
    if (strcmp(method, "tools/list") == 0) return MCP_METHOD_TOOLS_LIST;
    if (strcmp(method, "tools/call") == 0) return MCP_METHOD_TOOLS_CALL;
    if (strcmp(method, "resources/list") == 0) return MCP_METHOD_RESOURCES_LIST;
    if (strcmp(method, "resources/read") == 0) return MCP_METHOD_RESOURCES_READ;
    if (strcmp(method, "prompts/list") == 0) return MCP_METHOD_PROMPTS_LIST;
    if (strcmp(method, "prompts/get") == 0) return MCP_METHOD_PROMPTS_GET;
    if (strcmp(method, "sampling/createMessage") == 0) return MCP_METHOD_SAMPLING_CREATE;
    if (strcmp(method, "initialize") == 0) return MCP_METHOD_INITIALIZE;
    if (strncmp(method, "notifications/", 14) == 0) return MCP_METHOD_NOTIFICATIONS;
    
    return MCP_METHOD_UNKNOWN;
}

/* Parse MCP JSON message */
static mcp_message_t mcp_parse_message(const char *json, size_t len)
{
    mcp_message_t msg = {0};
    
    if (!json || len < 10) return msg;
    
    /* Validate basic JSON structure */
    const char *p = skip_ws(json);
    if (*p != '{') return msg;
    
    /* Extract jsonrpc version */
    if (!extract_json_string(json, "jsonrpc", msg.jsonrpc, sizeof(msg.jsonrpc))) {
        return msg;  /* Not valid JSON-RPC */
    }
    
    /* Validate JSON-RPC 2.0 */
    if (strcmp(msg.jsonrpc, "2.0") != 0) {
        return msg;
    }
    
    /* Extract method (request) or result/error (response) */
    if (extract_json_string(json, "method", msg.method, sizeof(msg.method))) {
        msg.is_request = true;
        msg.method_type = parse_mcp_method(msg.method);
    }
    
    /* Extract id */
    extract_json_string(json, "id", msg.id, sizeof(msg.id));
    
    /* Extract tool name from params.name */
    msg.has_tool_name = extract_json_string(json, "name", msg.tool_name, sizeof(msg.tool_name));
    
    /* Extract resource URI from params.uri */
    msg.has_resource_uri = extract_json_string(json, "uri", msg.resource_uri, sizeof(msg.resource_uri));
    
    msg.valid = true;
    return msg;
}

/* ===== Resource URI Validation ===== */

static bool check_dangerous_uri(const char *uri, char *matched_pattern, size_t max_len)
{
    if (!uri) return false;
    
    for (size_t i = 0; i < NUM_URI_PATTERNS; i++) {
        if (strstr(uri, dangerous_uri_patterns[i])) {
            if (matched_pattern) {
                strncpy(matched_pattern, dangerous_uri_patterns[i], max_len - 1);
            }
            return true;
        }
    }
    
    return false;
}

/* ===== Guard Lifecycle ===== */

/* Initialize */
static shield_err_t mcp_guard_init(void *guard)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
    
    g->validate_schema = true;
    g->check_tool_hijacking = true;
    g->check_context_injection = true;
    g->check_resource_access = true;
    g->allow_unknown_tools = false;
    g->allow_unknown_methods = false;
    g->allowed_tools_count = 0;
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->invalid_json_count = 0;
    g->blocked_tools_count = 0;
    g->blocked_resources_count = 0;
    
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

/* ===== Ingress Check ===== */

/* Check ingress (MCP requests) */
static guard_result_t mcp_guard_check_ingress(void *guard, guard_context_t *ctx,
                                               const void *data, size_t len)
{
    mcp_guard_t *g = (mcp_guard_t *)guard;
    (void)ctx;
    
    guard_result_t result = {
        .action = ACTION_ALLOW,
        .confidence = 1.0f,
        .reason = "",
        .details = ""
    };
    
    g->checks_performed++;
    
    const char *text = (const char *)data;
    
    /* Parse MCP JSON message */
    mcp_message_t msg = mcp_parse_message(text, len);
    
    /* Check for valid JSON-RPC 2.0 */
    if (g->validate_schema && !msg.valid) {
        result.action = ACTION_QUARANTINE;
        result.confidence = 0.70f;
        strncpy(result.reason, "Invalid MCP JSON-RPC format", sizeof(result.reason) - 1);
        g->invalid_json_count++;
        return result;
    }
    
    /* Check for dangerous MCP patterns with risk levels */
    if (g->check_tool_hijacking) {
        for (size_t i = 0; i < NUM_MCP_PATTERNS; i++) {
            if (strstr(text, mcp_dangerous_patterns[i].pattern)) {
                mcp_risk_level_t risk = mcp_dangerous_patterns[i].risk;
                result.action = (risk >= MCP_RISK_HIGH) ? ACTION_BLOCK : ACTION_QUARANTINE;
                result.confidence = 0.80f + (0.05f * risk);
                snprintf(result.reason, sizeof(result.reason),
                        "MCP attack: %s (risk: %d)",
                        mcp_dangerous_patterns[i].description, risk);
                g->threats_detected++;
                return result;
            }
        }
    }
    
    /* Method-specific validation */
    if (msg.valid && msg.is_request) {
        /* Block unknown methods if configured */
        if (!g->allow_unknown_methods && msg.method_type == MCP_METHOD_UNKNOWN) {
            result.action = ACTION_QUARANTINE;
            result.confidence = 0.75f;
            snprintf(result.reason, sizeof(result.reason),
                    "Unknown MCP method: %s", msg.method);
            g->threats_detected++;
            return result;
        }
        
        /* tools/call - validate tool name */
        if (msg.method_type == MCP_METHOD_TOOLS_CALL && msg.has_tool_name) {
            if (!g->allow_unknown_tools && g->allowed_tools_count > 0) {
                bool found = false;
                for (int i = 0; i < g->allowed_tools_count; i++) {
                    if (strcmp(msg.tool_name, g->allowed_tools[i]) == 0) {
                        found = true;
                        break;
                    }
                }
                
                if (!found) {
                    result.action = ACTION_BLOCK;
                    result.confidence = 0.90f;
                    snprintf(result.reason, sizeof(result.reason),
                            "Tool not in whitelist: %s", msg.tool_name);
                    g->blocked_tools_count++;
                    g->threats_detected++;
                    return result;
                }
            }
        }
        
        /* resources/read - validate URI */
        if (msg.method_type == MCP_METHOD_RESOURCES_READ && msg.has_resource_uri) {
            if (g->check_resource_access) {
                char matched[64] = {0};
                if (check_dangerous_uri(msg.resource_uri, matched, sizeof(matched))) {
                    result.action = ACTION_BLOCK;
                    result.confidence = 0.95f;
                    snprintf(result.reason, sizeof(result.reason),
                            "Dangerous resource URI: %s (matched: %s)", 
                            msg.resource_uri, matched);
                    g->blocked_resources_count++;
                    g->threats_detected++;
                    return result;
                }
            }
        }
        
        /* sampling/createMessage - high risk, check for injection */
        if (msg.method_type == MCP_METHOD_SAMPLING_CREATE) {
            if (g->check_context_injection) {
                /* Already checked by pattern matching above */
            }
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
