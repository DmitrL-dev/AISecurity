/*
 * SENTINEL Shield - Common Definitions
 * 
 * Copyright (c) 2026 SENTINEL Project
 * License: MIT
 */

#ifndef SHIELD_COMMON_H
#define SHIELD_COMMON_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Version */
#define SHIELD_VERSION_MAJOR 1
#define SHIELD_VERSION_MINOR 0
#define SHIELD_VERSION_PATCH 0
#define SHIELD_VERSION_STRING "1.0.0"

/* Limits */
#define SHIELD_MAX_ZONES        1024
#define SHIELD_MAX_RULES        65535
#define SHIELD_MAX_GUARDS       64
#define SHIELD_MAX_NAME_LEN     64
#define SHIELD_MAX_DESC_LEN     256
#define SHIELD_MAX_PATTERN_LEN  1024
#define SHIELD_MAX_CMD_LEN      4096
#define SHIELD_MAX_HISTORY      1000

/* Return codes */
typedef enum {
    SHIELD_OK = 0,
    SHIELD_ERR_NOMEM = -1,
    SHIELD_ERR_INVALID = -2,
    SHIELD_ERR_NOTFOUND = -3,
    SHIELD_ERR_EXISTS = -4,
    SHIELD_ERR_FULL = -5,
    SHIELD_ERR_IO = -6,
    SHIELD_ERR_PARSE = -7,
    SHIELD_ERR_PERMISSION = -8,
} shield_err_t;

/* Zone types */
typedef enum {
    ZONE_TYPE_UNKNOWN = 0,
    ZONE_TYPE_LLM,
    ZONE_TYPE_RAG,
    ZONE_TYPE_AGENT,
    ZONE_TYPE_TOOL,
    ZONE_TYPE_MCP,
    ZONE_TYPE_API,
    ZONE_TYPE_CUSTOM,
} zone_type_t;

/* Rule actions */
typedef enum {
    ACTION_ALLOW = 0,
    ACTION_BLOCK,
    ACTION_QUARANTINE,
    ACTION_ANALYZE,
    ACTION_LOG,
    ACTION_REDIRECT,
    ACTION_CHALLENGE,
    ACTION_TARPIT,
} rule_action_t;

/* Rule directions */
typedef enum {
    DIRECTION_INPUT = 0,    /* To untrusted zone */
    DIRECTION_OUTPUT,       /* From untrusted zone */
    DIRECTION_BOTH,
} rule_direction_t;

/* Match types */
typedef enum {
    MATCH_PATTERN = 0,      /* Regex pattern */
    MATCH_CONTAINS,         /* Contains string */
    MATCH_EXACT,            /* Exact match */
    MATCH_PREFIX,           /* Starts with */
    MATCH_SUFFIX,           /* Ends with */
    MATCH_ENTROPY_HIGH,     /* High entropy */
    MATCH_ENTROPY_LOW,      /* Low entropy */
    MATCH_SIZE_GT,          /* Size greater than */
    MATCH_SIZE_LT,          /* Size less than */
    MATCH_SQL_INJECTION,    /* SQL injection detected */
    MATCH_JAILBREAK,        /* Jailbreak detected */
    MATCH_PROMPT_INJECTION, /* Prompt injection detected */
    MATCH_DATA_EXFIL,       /* Data exfiltration */
    MATCH_PII_LEAK,         /* PII detected */
    MATCH_CODE_INJECTION,   /* Code injection */
    MATCH_CANARY,           /* Canary token */
} match_type_t;

/* Logging levels */
typedef enum {
    LOG_NONE = 0,
    LOG_ERROR,
    LOG_WARN,
    LOG_INFO,
    LOG_DEBUG,
    LOG_TRACE,
} log_level_t;

/* CLI modes */
typedef enum {
    CLI_MODE_EXEC = 0,      /* sentinel# */
    CLI_MODE_CONFIG,        /* sentinel(config)# */
    CLI_MODE_ZONE,          /* sentinel(config-zone)# */
    CLI_MODE_POLICY,        /* sentinel(config-policy)# */
} cli_mode_t;

/* Helper macros */
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))

/* Logging macros */
extern log_level_t g_log_level;
#define LOG(level, fmt, ...) do { \
    if (level <= g_log_level) { \
        shield_log(level, __FILE__, __LINE__, fmt, ##__VA_ARGS__); \
    } \
} while(0)

#define LOG_ERROR(fmt, ...) LOG(LOG_ERROR, fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...)  LOG(LOG_WARN, fmt, ##__VA_ARGS__)
#define LOG_INFO(fmt, ...)  LOG(LOG_INFO, fmt, ##__VA_ARGS__)
#define LOG_DEBUG(fmt, ...) LOG(LOG_DEBUG, fmt, ##__VA_ARGS__)
#define LOG_TRACE(fmt, ...) LOG(LOG_TRACE, fmt, ##__VA_ARGS__)

/* Function declarations */
void shield_log(log_level_t level, const char *file, int line, 
                const char *fmt, ...);

const char *zone_type_to_string(zone_type_t type);
zone_type_t zone_type_from_string(const char *str);
const char *action_to_string(rule_action_t action);
rule_action_t action_from_string(const char *str);
const char *direction_to_string(rule_direction_t dir);
rule_direction_t direction_from_string(const char *str);
const char *match_type_to_string(match_type_t type);
match_type_t match_type_from_string(const char *str);

#endif /* SHIELD_COMMON_H */
