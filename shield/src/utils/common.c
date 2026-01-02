/*
 * SENTINEL Shield - Common Utilities
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>

#include "shield_common.h"

/* Global log level */
extern log_level_t g_log_level;

/* Log level strings */
static const char *log_level_strings[] = {
    "NONE",
    "ERROR",
    "WARN",
    "INFO",
    "DEBUG",
    "TRACE",
};

/* Zone type strings */
static const char *zone_type_strings[] = {
    "unknown",
    "llm",
    "rag",
    "agent",
    "tool",
    "mcp",
    "api",
    "custom",
};

/* Action strings */
static const char *action_strings[] = {
    "allow",
    "block",
    "quarantine",
    "analyze",
    "log",
    "redirect",
    "challenge",
    "tarpit",
};

/* Direction strings */
static const char *direction_strings[] = {
    "input",
    "output",
    "both",
};

/* Match type strings */
static const char *match_type_strings[] = {
    "pattern",
    "contains",
    "exact",
    "prefix",
    "suffix",
    "entropy-high",
    "entropy-low",
    "size-gt",
    "size-lt",
    "sql-injection",
    "jailbreak",
    "prompt-injection",
    "data-exfil",
    "pii-leak",
    "code-injection",
    "canary",
};

/* Logging function */
void shield_log(log_level_t level, const char *file, int line,
                const char *fmt, ...)
{
    if (level > g_log_level) {
        return;
    }
    
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char time_buf[32];
    strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", tm);
    
    fprintf(stderr, "[%s] [%s] %s:%d: ", 
            time_buf, log_level_strings[level], file, line);
    
    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    
    fprintf(stderr, "\n");
}

/* Zone type conversions */
const char *zone_type_to_string(zone_type_t type)
{
    if (type >= 0 && type < (int)ARRAY_SIZE(zone_type_strings)) {
        return zone_type_strings[type];
    }
    return "unknown";
}

zone_type_t zone_type_from_string(const char *str)
{
    if (!str) {
        return ZONE_TYPE_UNKNOWN;
    }
    
    for (size_t i = 0; i < ARRAY_SIZE(zone_type_strings); i++) {
        if (strcasecmp(str, zone_type_strings[i]) == 0) {
            return (zone_type_t)i;
        }
    }
    
    return ZONE_TYPE_UNKNOWN;
}

/* Action conversions */
const char *action_to_string(rule_action_t action)
{
    if (action >= 0 && action < (int)ARRAY_SIZE(action_strings)) {
        return action_strings[action];
    }
    return "unknown";
}

rule_action_t action_from_string(const char *str)
{
    if (!str) {
        return ACTION_ALLOW;
    }
    
    for (size_t i = 0; i < ARRAY_SIZE(action_strings); i++) {
        if (strcasecmp(str, action_strings[i]) == 0) {
            return (rule_action_t)i;
        }
    }
    
    return ACTION_ALLOW;
}

/* Direction conversions */
const char *direction_to_string(rule_direction_t dir)
{
    if (dir >= 0 && dir < (int)ARRAY_SIZE(direction_strings)) {
        return direction_strings[dir];
    }
    return "unknown";
}

rule_direction_t direction_from_string(const char *str)
{
    if (!str) {
        return DIRECTION_INPUT;
    }
    
    for (size_t i = 0; i < ARRAY_SIZE(direction_strings); i++) {
        if (strcasecmp(str, direction_strings[i]) == 0) {
            return (rule_direction_t)i;
        }
    }
    
    /* Aliases */
    if (strcasecmp(str, "in") == 0 || strcasecmp(str, "ingress") == 0) {
        return DIRECTION_INPUT;
    }
    if (strcasecmp(str, "out") == 0 || strcasecmp(str, "egress") == 0) {
        return DIRECTION_OUTPUT;
    }
    
    return DIRECTION_INPUT;
}

/* Match type conversions */
const char *match_type_to_string(match_type_t type)
{
    if (type >= 0 && type < (int)ARRAY_SIZE(match_type_strings)) {
        return match_type_strings[type];
    }
    return "unknown";
}

match_type_t match_type_from_string(const char *str)
{
    if (!str) {
        return MATCH_PATTERN;
    }
    
    for (size_t i = 0; i < ARRAY_SIZE(match_type_strings); i++) {
        if (strcasecmp(str, match_type_strings[i]) == 0) {
            return (match_type_t)i;
        }
    }
    
    /* Aliases */
    if (strcasecmp(str, "regex") == 0) {
        return MATCH_PATTERN;
    }
    
    return MATCH_PATTERN;
}
