/**
 * @file shield_log.h
 * @brief Logging macros for SENTINEL Shield
 */

#ifndef SENTINEL_SHIELD_LOG_H
#define SENTINEL_SHIELD_LOG_H

#include <stdio.h>

/* Log levels */
typedef enum {
    SHIELD_LOG_DEBUG = 0,
    SHIELD_LOG_INFO,
    SHIELD_LOG_WARN,
    SHIELD_LOG_ERROR,
    SHIELD_LOG_FATAL
} shield_log_level_t;

/* Simple logging macros */
#define SHIELD_LOG_DEBUG(...) fprintf(stderr, "[DEBUG] " __VA_ARGS__), fprintf(stderr, "\n")
#define SHIELD_LOG_INFO(...)  fprintf(stderr, "[INFO]  " __VA_ARGS__), fprintf(stderr, "\n")
#define SHIELD_LOG_WARN(...)  fprintf(stderr, "[WARN]  " __VA_ARGS__), fprintf(stderr, "\n")
#define SHIELD_LOG_ERROR(...) fprintf(stderr, "[ERROR] " __VA_ARGS__), fprintf(stderr, "\n")
#define SHIELD_LOG_FATAL(...) fprintf(stderr, "[FATAL] " __VA_ARGS__), fprintf(stderr, "\n")

#endif /* SENTINEL_SHIELD_LOG_H */
