/*
 * SENTINEL Shield - Global Variables
 * 
 * Global variable definitions that are declared extern in headers.
 * This file provides the actual storage.
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "shield_common.h"

/* ============== Global Variables ============== */

/* Logging level (used by LOG_* macros) */
log_level_t g_log_level = LOG_INFO;  /* Default: INFO */

/* Global subsystem pointers (NULL by default, initialized by subsystem init functions) */
void *g_metrics = NULL;
void *g_cluster = NULL;
void *g_health = NULL;
void *g_plugins = NULL;
void *g_canaries = NULL;
