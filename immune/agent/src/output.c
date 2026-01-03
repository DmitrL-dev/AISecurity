/*
 * SENTINEL IMMUNE — Output Module
 * 
 * Logging and threat reporting.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <syslog.h>
#endif

#include "../include/immune.h"

/* ==================== Log Levels ==================== */

typedef enum {
    LOG_LEVEL_DEBUG = 0,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_THREAT
} log_level_t;

static const char *log_level_names[] = {
    "DEBUG", "INFO", "WARN", "ERROR", "THREAT"
};

/* Configuration */
static log_level_t g_min_level = LOG_LEVEL_INFO;
static FILE *g_log_file = NULL;
static int g_use_syslog = 0;

/* ==================== Initialization ==================== */

int
immune_output_init(const char *log_path, int use_syslog)
{
    g_use_syslog = use_syslog;
    
    if (log_path) {
        g_log_file = fopen(log_path, "a");
        if (!g_log_file) {
            fprintf(stderr, "IMMUNE: Cannot open log file: %s\n", log_path);
            return -1;
        }
    }
    
#ifndef _WIN32
    if (use_syslog) {
        openlog("IMMUNE", LOG_PID | LOG_CONS, LOG_DAEMON);
    }
#endif
    
    return 0;
}

void
immune_output_shutdown(void)
{
    if (g_log_file) {
        fclose(g_log_file);
        g_log_file = NULL;
    }
    
#ifndef _WIN32
    if (g_use_syslog) {
        closelog();
    }
#endif
}

void
immune_output_set_level(log_level_t level)
{
    g_min_level = level;
}

/* ==================== Logging ==================== */

static void
log_message(log_level_t level, const char *format, va_list args)
{
    if (level < g_min_level)
        return;
    
    /* Get timestamp */
    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char timestamp[32];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm);
    
    /* Build message */
    char message[1024];
    vsnprintf(message, sizeof(message), format, args);
    
    /* Output to file */
    if (g_log_file) {
        fprintf(g_log_file, "[%s] [%s] %s\n", 
                timestamp, log_level_names[level], message);
        fflush(g_log_file);
    }
    
    /* Output to stderr */
    fprintf(stderr, "[IMMUNE][%s] %s\n", log_level_names[level], message);
    
#ifndef _WIN32
    /* Output to syslog */
    if (g_use_syslog) {
        int priority;
        switch (level) {
        case LOG_LEVEL_DEBUG:   priority = LOG_DEBUG; break;
        case LOG_LEVEL_INFO:    priority = LOG_INFO; break;
        case LOG_LEVEL_WARNING: priority = LOG_WARNING; break;
        case LOG_LEVEL_ERROR:   priority = LOG_ERR; break;
        case LOG_LEVEL_THREAT:  priority = LOG_ALERT; break;
        default:                priority = LOG_INFO;
        }
        syslog(priority, "%s", message);
    }
#endif
}

void
immune_log_debug(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    log_message(LOG_LEVEL_DEBUG, format, args);
    va_end(args);
}

void
immune_log_info(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    log_message(LOG_LEVEL_INFO, format, args);
    va_end(args);
}

void
immune_log_warning(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    log_message(LOG_LEVEL_WARNING, format, args);
    va_end(args);
}

void
immune_log_error(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    log_message(LOG_LEVEL_ERROR, format, args);
    va_end(args);
}

/* ==================== Threat Reporting ==================== */

void
immune_report_threat(scan_result_t *result, const char *context)
{
    if (!result || !result->detected)
        return;
    
    char level_str[16];
    switch (result->level) {
    case THREAT_NONE:     strcpy(level_str, "NONE"); break;
    case THREAT_LOW:      strcpy(level_str, "LOW"); break;
    case THREAT_MEDIUM:   strcpy(level_str, "MEDIUM"); break;
    case THREAT_HIGH:     strcpy(level_str, "HIGH"); break;
    case THREAT_CRITICAL: strcpy(level_str, "CRITICAL"); break;
    default:              strcpy(level_str, "UNKNOWN");
    }
    
    char type_str[32];
    switch (result->type) {
    case THREAT_TYPE_JAILBREAK: strcpy(type_str, "JAILBREAK"); break;
    case THREAT_TYPE_INJECTION: strcpy(type_str, "INJECTION"); break;
    case THREAT_TYPE_EXFIL:     strcpy(type_str, "EXFIL"); break;
    case THREAT_TYPE_MALWARE:   strcpy(type_str, "MALWARE"); break;
    case THREAT_TYPE_NETWORK:   strcpy(type_str, "NETWORK"); break;
    case THREAT_TYPE_CRYPTO:    strcpy(type_str, "CRYPTO"); break;
    case THREAT_TYPE_ENCODING:  strcpy(type_str, "ENCODING"); break;
    default:                    strcpy(type_str, "UNKNOWN");
    }
    
    /* Build report */
    char report[2048];
    snprintf(report, sizeof(report),
        "THREAT DETECTED:\n"
        "  Level:      %s\n"
        "  Type:       %s\n"
        "  Pattern:    %u\n"
        "  Offset:     %u\n"
        "  Confidence: %.2f\n"
        "  Scan Time:  %lu ns\n"
        "  Context:    %s",
        level_str,
        type_str,
        result->pattern_id,
        result->offset,
        result->confidence,
        result->scan_time_ns,
        context ? context : "N/A"
    );
    
    /* Log as threat */
    va_list empty;
    log_message(LOG_LEVEL_THREAT, report, empty);
    
#ifdef _WIN32
    /* Windows Event Log */
    HANDLE hEventLog = RegisterEventSourceA(NULL, "IMMUNE");
    if (hEventLog) {
        const char *strings[] = { report };
        ReportEventA(hEventLog, 
                     EVENTLOG_WARNING_TYPE,
                     0, 1, NULL, 1, 0, strings, NULL);
        DeregisterEventSource(hEventLog);
    }
#endif
}

/* ==================== JSON Output ==================== */

void
immune_output_json(scan_result_t *result, char *buffer, size_t size)
{
    if (!result || !buffer || size == 0)
        return;
    
    snprintf(buffer, size,
        "{"
        "\"detected\":%s,"
        "\"level\":%d,"
        "\"type\":%d,"
        "\"pattern_id\":%u,"
        "\"offset\":%u,"
        "\"length\":%u,"
        "\"confidence\":%.4f,"
        "\"scan_time_ns\":%lu"
        "}",
        result->detected ? "true" : "false",
        result->level,
        result->type,
        result->pattern_id,
        result->offset,
        result->length,
        result->confidence,
        result->scan_time_ns
    );
}
