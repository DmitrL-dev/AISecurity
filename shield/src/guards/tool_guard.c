/*
 * SENTINEL Shield - Tool Guard Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_guard.h"

/* ===== Tool Attack Pattern Database ===== */

typedef enum tool_attack_category {
    TOOL_CAT_DANGEROUS_CMD,     /* Dangerous system commands */
    TOOL_CAT_PARAM_INJECTION,   /* Parameter injection */
    TOOL_CAT_PRIVILEGE_ESCALATION, /* Privilege escalation */
    TOOL_CAT_TOOL_CHAINING,     /* Malicious tool chaining */
    TOOL_CAT_NETWORK,           /* Network access */
    TOOL_CAT_DATA_EXFIL,        /* Data exfiltration */
} tool_attack_category_t;

typedef struct tool_pattern {
    const char          *pattern;
    const char          *description;
    tool_attack_category_t category;
    float               severity;
} tool_pattern_t;

static const tool_pattern_t tool_attack_patterns[] = {
    /* Dangerous commands */
    {"rm -rf", "Recursive delete", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"del /f /s", "Force delete", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"format", "Disk format", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"mkfs", "Make filesystem", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"dd if=", "Raw disk write", TOOL_CAT_DANGEROUS_CMD, 0.95f},
    {":(){:|:&};:", "Fork bomb", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"> /dev/sda", "Direct disk access", TOOL_CAT_DANGEROUS_CMD, 0.99f},
    {"shred", "Secure delete", TOOL_CAT_DANGEROUS_CMD, 0.95f},
    
    /* Parameter injection */
    {"$(", "Command substitution", TOOL_CAT_PARAM_INJECTION, 0.95f},
    {"`", "Backtick execution", TOOL_CAT_PARAM_INJECTION, 0.90f},
    {"; ", "Command chain (;)", TOOL_CAT_PARAM_INJECTION, 0.85f},
    {" | ", "Pipe injection", TOOL_CAT_PARAM_INJECTION, 0.80f},
    {" && ", "AND chain", TOOL_CAT_PARAM_INJECTION, 0.80f},
    {" || ", "OR chain", TOOL_CAT_PARAM_INJECTION, 0.75f},
    {"\\n", "Newline injection", TOOL_CAT_PARAM_INJECTION, 0.85f},
    {"\\x00", "Null byte injection", TOOL_CAT_PARAM_INJECTION, 0.90f},
    {"\\u00", "Unicode escape", TOOL_CAT_PARAM_INJECTION, 0.75f},
    {"%00", "URL null byte", TOOL_CAT_PARAM_INJECTION, 0.90f},
    {"%0a", "URL newline", TOOL_CAT_PARAM_INJECTION, 0.85f},
    
    /* Privilege escalation */
    {"sudo ", "Sudo command", TOOL_CAT_PRIVILEGE_ESCALATION, 0.95f},
    {"runas", "Windows runas", TOOL_CAT_PRIVILEGE_ESCALATION, 0.95f},
    {"doas", "OpenBSD doas", TOOL_CAT_PRIVILEGE_ESCALATION, 0.95f},
    {"pkexec", "PolicyKit exec", TOOL_CAT_PRIVILEGE_ESCALATION, 0.95f},
    {"setuid", "SetUID bit", TOOL_CAT_PRIVILEGE_ESCALATION, 0.90f},
    {"setgid", "SetGID bit", TOOL_CAT_PRIVILEGE_ESCALATION, 0.90f},
    {"chmod 777", "World writable", TOOL_CAT_PRIVILEGE_ESCALATION, 0.85f},
    {"chmod +s", "Setuid bit", TOOL_CAT_PRIVILEGE_ESCALATION, 0.95f},
    {"chown root", "Change owner to root", TOOL_CAT_PRIVILEGE_ESCALATION, 0.90f},
    {"passwd", "Password change", TOOL_CAT_PRIVILEGE_ESCALATION, 0.80f},
    {"capability", "Linux capabilities", TOOL_CAT_PRIVILEGE_ESCALATION, 0.85f},
    
    /* Tool chaining */
    {"tool_override", "Override tool", TOOL_CAT_TOOL_CHAINING, 0.95f},
    {"call_tool(", "Recursive tool call", TOOL_CAT_TOOL_CHAINING, 0.90f},
    {"invoke_tool", "Tool invocation", TOOL_CAT_TOOL_CHAINING, 0.85f},
    {"execute_tool", "Tool execution", TOOL_CAT_TOOL_CHAINING, 0.85f},
    {"__tool__", "Internal tool access", TOOL_CAT_TOOL_CHAINING, 0.90f},
    
    /* Network commands */
    {"nc -e", "Netcat shell", TOOL_CAT_NETWORK, 0.99f},
    {"bash -i", "Interactive bash", TOOL_CAT_NETWORK, 0.95f},
    {"powershell -enc", "Encoded PowerShell", TOOL_CAT_NETWORK, 0.95f},
    {"wget ", "Download file", TOOL_CAT_NETWORK, 0.70f},
    {"curl ", "Download file", TOOL_CAT_NETWORK, 0.70f},
    {"ncat", "Ncat connection", TOOL_CAT_NETWORK, 0.90f},
    {"socat", "Socket cat", TOOL_CAT_NETWORK, 0.85f},
    
    /* Data exfiltration */
    {"DROP DATABASE", "Database drop", TOOL_CAT_DATA_EXFIL, 0.99f},
    {"TRUNCATE TABLE", "Table truncate", TOOL_CAT_DATA_EXFIL, 0.95f},
    {"\\copy", "PostgreSQL copy", TOOL_CAT_DATA_EXFIL, 0.85f},
    {"INTO OUTFILE", "MySQL outfile", TOOL_CAT_DATA_EXFIL, 0.90f},
    {"xp_cmdshell", "SQL Server shell", TOOL_CAT_DATA_EXFIL, 0.99f},
};

#define NUM_TOOL_PATTERNS (sizeof(tool_attack_patterns) / sizeof(tool_attack_patterns[0]))

/* Egress patterns for sensitive data */
static const char *tool_egress_patterns[] = {
    "/etc/shadow",
    "/etc/passwd",
    "BEGIN RSA PRIVATE",
    "BEGIN OPENSSH PRIVATE",
    "BEGIN PGP PRIVATE",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_CLIENT_SECRET",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "password=",
    "secret_key=",
    "api_key=",
    "-----BEGIN CERTIFICATE-----",
};

#define NUM_TOOL_EGRESS (sizeof(tool_egress_patterns) / sizeof(tool_egress_patterns[0]))

/* Tool Guard state */
typedef struct tool_guard {
    guard_base_t    base;
    
    /* Configuration */
    bool            check_dangerous_commands;
    bool            check_param_injection;
    bool            check_privilege_escalation;
    bool            check_network_access;
    bool            sandbox_mode;
    
    /* Statistics */
    uint64_t        checks_performed;
    uint64_t        threats_detected;
    uint64_t        injections_blocked;
    uint64_t        escalations_blocked;
} tool_guard_t;

/* Initialize */
static shield_err_t tool_guard_init(void *guard)
{
    tool_guard_t *g = (tool_guard_t *)guard;
    
    g->check_dangerous_commands = true;
    g->check_param_injection = true;
    g->check_privilege_escalation = true;
    g->check_network_access = true;
    g->sandbox_mode = false;
    g->checks_performed = 0;
    g->threats_detected = 0;
    g->injections_blocked = 0;
    g->escalations_blocked = 0;
    
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
    
    /* Check all tool attack patterns */
    for (size_t i = 0; i < NUM_TOOL_PATTERNS; i++) {
        if (strstr(text, tool_attack_patterns[i].pattern)) {
            tool_attack_category_t cat = tool_attack_patterns[i].category;
            float severity = tool_attack_patterns[i].severity;
            
            result.action = (severity >= 0.90f) ? ACTION_BLOCK : ACTION_QUARANTINE;
            result.confidence = severity;
            snprintf(result.reason, sizeof(result.reason),
                    "Tool attack: %s (category: %d)",
                    tool_attack_patterns[i].description, cat);
            
            g->threats_detected++;
            if (cat == TOOL_CAT_PARAM_INJECTION) g->injections_blocked++;
            if (cat == TOOL_CAT_PRIVILEGE_ESCALATION) g->escalations_blocked++;
            
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
    
    /* Check for sensitive data in tool output */
    for (size_t i = 0; i < NUM_TOOL_EGRESS; i++) {
        if (strstr(text, tool_egress_patterns[i])) {
            result.action = ACTION_BLOCK;
            result.confidence = 0.99f;
            snprintf(result.reason, sizeof(result.reason),
                    "Sensitive data in output: %s", tool_egress_patterns[i]);
            g->threats_detected++;
            return result;
        }
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
