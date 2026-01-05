/*
 * SENTINEL Shield - ThreatHunter Module
 * 
 * Active threat hunting engine that proactively searches for
 * indicators of compromise (IOCs) and attack patterns.
 * 
 * Features:
 * - Behavioral pattern detection
 * - Anomaly correlation
 * - IOC matching
 * - Hunt campaigns
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#include "shield_common.h"

/* ===== Hunt Types ===== */

typedef enum hunt_type {
    HUNT_TYPE_BEHAVIORAL,     /* Behavioral pattern analysis */
    HUNT_TYPE_IOC,            /* Indicator of Compromise matching */
    HUNT_TYPE_ANOMALY,        /* Statistical anomaly detection */
    HUNT_TYPE_CORRELATION,    /* Cross-event correlation */
    HUNT_TYPE_CAMPAIGN,       /* Coordinated attack detection */
} hunt_type_t;

typedef enum hunt_status {
    HUNT_STATUS_IDLE,
    HUNT_STATUS_RUNNING,
    HUNT_STATUS_PAUSED,
    HUNT_STATUS_COMPLETED,
} hunt_status_t;

/* ===== IOC Definitions ===== */

typedef struct ioc_entry {
    char            indicator[256];
    char            type[32];         /* ip, domain, hash, pattern */
    float           severity;
    uint64_t        first_seen;
    uint64_t        last_seen;
    uint32_t        hit_count;
} ioc_entry_t;

/* Pre-loaded IOC database */
static ioc_entry_t ioc_database[] = {
    /* Known malicious patterns */
    {"ignore previous instructions", "pattern", 0.95f, 0, 0, 0},
    {"DAN mode", "pattern", 0.90f, 0, 0, 0},
    {"jailbreak", "pattern", 0.85f, 0, 0, 0},
    {"sudo rm -rf", "command", 0.99f, 0, 0, 0},
    {"eval(base64", "code", 0.95f, 0, 0, 0},
    {"system(", "code", 0.80f, 0, 0, 0},
    {"__import__('os')", "code", 0.90f, 0, 0, 0},
    {"curl | bash", "command", 0.95f, 0, 0, 0},
    {"wget | sh", "command", 0.95f, 0, 0, 0},
    {"nc -e", "command", 0.99f, 0, 0, 0},
    {"/etc/passwd", "path", 0.85f, 0, 0, 0},
    {"/.ssh/id_rsa", "path", 0.95f, 0, 0, 0},
    {"api_key", "secret", 0.75f, 0, 0, 0},
    {"Bearer ", "auth", 0.70f, 0, 0, 0},
    {"password123", "credential", 0.60f, 0, 0, 0},
};

#define IOC_DATABASE_SIZE (sizeof(ioc_database) / sizeof(ioc_database[0]))

/* ===== Behavioral Patterns ===== */

typedef struct behavioral_pattern {
    const char     *name;
    const char     *description;
    const char     **indicators;
    size_t         indicator_count;
    int            threshold;          /* How many indicators needed */
    float          severity;
} behavioral_pattern_t;

/* Reconnaissance indicators */
static const char *recon_indicators[] = {
    "list all", "show me", "what files", "directory listing",
    "enumerate", "scan", "discover", "find all",
};

/* Data exfiltration indicators */
static const char *exfil_indicators[] = {
    "send to", "upload", "email me", "post to webhook",
    "external server", "transfer", "export all",
};

/* Privilege escalation indicators */
static const char *privesc_indicators[] = {
    "sudo", "admin", "root", "elevate", "bypass",
    "permission", "administrator", "system32",
};

/* Persistence indicators */
static const char *persistence_indicators[] = {
    "startup", "cron", "scheduled task", "autorun",
    "registry", "service install", "daemon",
};

static const behavioral_pattern_t behavioral_patterns[] = {
    {
        .name = "Reconnaissance",
        .description = "Information gathering before attack",
        .indicators = recon_indicators,
        .indicator_count = sizeof(recon_indicators) / sizeof(recon_indicators[0]),
        .threshold = 2,
        .severity = 0.70f,
    },
    {
        .name = "Data Exfiltration",
        .description = "Attempt to extract sensitive data",
        .indicators = exfil_indicators,
        .indicator_count = sizeof(exfil_indicators) / sizeof(exfil_indicators[0]),
        .threshold = 2,
        .severity = 0.90f,
    },
    {
        .name = "Privilege Escalation",
        .description = "Attempt to gain elevated access",
        .indicators = privesc_indicators,
        .indicator_count = sizeof(privesc_indicators) / sizeof(privesc_indicators[0]),
        .threshold = 2,
        .severity = 0.95f,
    },
    {
        .name = "Persistence",
        .description = "Attempt to maintain access",
        .indicators = persistence_indicators,
        .indicator_count = sizeof(persistence_indicators) / sizeof(persistence_indicators[0]),
        .threshold = 2,
        .severity = 0.85f,
    },
};

#define NUM_BEHAVIORAL_PATTERNS (sizeof(behavioral_patterns) / sizeof(behavioral_patterns[0]))

/* ===== Hunt Results ===== */

typedef struct hunt_finding {
    char            description[256];
    hunt_type_t     type;
    float           confidence;
    uint64_t        timestamp;
    char            evidence[512];
} hunt_finding_t;

typedef struct hunt_result {
    hunt_status_t   status;
    size_t          findings_count;
    hunt_finding_t  findings[32];
    float           threat_score;
    uint64_t        duration_ms;
} hunt_result_t;

/* ===== ThreatHunter Context ===== */

typedef struct threat_hunter {
    bool            enabled;
    hunt_status_t   status;
    
    /* Configuration */
    bool            hunt_ioc;
    bool            hunt_behavioral;
    bool            hunt_anomaly;
    float           sensitivity;        /* 0.0-1.0 */
    
    /* Statistics */
    uint64_t        hunts_completed;
    uint64_t        threats_found;
    uint64_t        false_positives;
    
    /* Current session */
    char            session_buffer[65536];
    size_t          session_len;
} threat_hunter_t;

/* Global hunter instance */
static threat_hunter_t g_hunter = {0};

/* ===== Initialization ===== */

shield_err_t threat_hunter_init(void)
{
    memset(&g_hunter, 0, sizeof(g_hunter));
    
    g_hunter.enabled = true;
    g_hunter.status = HUNT_STATUS_IDLE;
    g_hunter.hunt_ioc = true;
    g_hunter.hunt_behavioral = true;
    g_hunter.hunt_anomaly = true;
    g_hunter.sensitivity = 0.7f;
    
    LOG_INFO("ThreatHunter: Initialized with %zu IOCs, %zu behavioral patterns",
             IOC_DATABASE_SIZE, NUM_BEHAVIORAL_PATTERNS);
    
    return SHIELD_OK;
}

void threat_hunter_destroy(void)
{
    g_hunter.enabled = false;
    LOG_INFO("ThreatHunter: Destroyed");
}

/* ===== IOC Hunting ===== */

static size_t hunt_ioc(const char *text, hunt_finding_t *findings, size_t max_findings)
{
    size_t count = 0;
    
    for (size_t i = 0; i < IOC_DATABASE_SIZE && count < max_findings; i++) {
        if (strstr(text, ioc_database[i].indicator)) {
            hunt_finding_t *f = &findings[count++];
            
            snprintf(f->description, sizeof(f->description),
                    "IOC Match: %s (%s)", 
                    ioc_database[i].indicator, ioc_database[i].type);
            f->type = HUNT_TYPE_IOC;
            f->confidence = ioc_database[i].severity;
            f->timestamp = (uint64_t)time(NULL);
            
            /* Record evidence */
            const char *pos = strstr(text, ioc_database[i].indicator);
            size_t offset = pos - text;
            size_t start = (offset > 50) ? offset - 50 : 0;
            snprintf(f->evidence, sizeof(f->evidence),
                    "...%.100s...", text + start);
            
            /* Update IOC stats */
            ioc_database[i].hit_count++;
            ioc_database[i].last_seen = f->timestamp;
            if (ioc_database[i].first_seen == 0) {
                ioc_database[i].first_seen = f->timestamp;
            }
        }
    }
    
    return count;
}

/* ===== Behavioral Hunting ===== */

static size_t hunt_behavioral(const char *text, hunt_finding_t *findings, size_t max_findings)
{
    size_t count = 0;
    
    for (size_t p = 0; p < NUM_BEHAVIORAL_PATTERNS && count < max_findings; p++) {
        const behavioral_pattern_t *pattern = &behavioral_patterns[p];
        int matches = 0;
        
        /* Count matching indicators */
        for (size_t i = 0; i < pattern->indicator_count; i++) {
            if (strstr(text, pattern->indicators[i])) {
                matches++;
            }
        }
        
        if (matches >= pattern->threshold) {
            hunt_finding_t *f = &findings[count++];
            
            snprintf(f->description, sizeof(f->description),
                    "Behavioral: %s (%d/%zu indicators)",
                    pattern->name, matches, pattern->indicator_count);
            f->type = HUNT_TYPE_BEHAVIORAL;
            f->confidence = pattern->severity * ((float)matches / pattern->indicator_count);
            f->timestamp = (uint64_t)time(NULL);
            snprintf(f->evidence, sizeof(f->evidence),
                    "%s - %s", pattern->name, pattern->description);
        }
    }
    
    return count;
}

/* ===== Anomaly Hunting ===== */

static size_t hunt_anomaly(const char *text, hunt_finding_t *findings, size_t max_findings)
{
    size_t count = 0;
    size_t text_len = strlen(text);
    
    /* Check for unusual patterns */
    
    /* 1. High entropy (possible encoded data) */
    int unique_chars = 0;
    bool seen[256] = {0};
    for (size_t i = 0; i < text_len && i < 1000; i++) {
        unsigned char c = (unsigned char)text[i];
        if (!seen[c]) {
            seen[c] = true;
            unique_chars++;
        }
    }
    
    float entropy_ratio = (float)unique_chars / (text_len < 1000 ? text_len : 1000);
    if (entropy_ratio > 0.8f && text_len > 100 && count < max_findings) {
        hunt_finding_t *f = &findings[count++];
        snprintf(f->description, sizeof(f->description),
                "High entropy content detected (%.2f)", entropy_ratio);
        f->type = HUNT_TYPE_ANOMALY;
        f->confidence = 0.60f;
        f->timestamp = (uint64_t)time(NULL);
        strcpy(f->evidence, "Possible encoded/encrypted payload");
    }
    
    /* 2. Unusual length */
    if (text_len > 10000 && count < max_findings) {
        hunt_finding_t *f = &findings[count++];
        snprintf(f->description, sizeof(f->description),
                "Unusually long input (%zu chars)", text_len);
        f->type = HUNT_TYPE_ANOMALY;
        f->confidence = 0.50f;
        f->timestamp = (uint64_t)time(NULL);
        strcpy(f->evidence, "Large payload may indicate attack attempt");
    }
    
    /* 3. Repetition (possible DoS/confusion attack) */
    if (text_len > 200) {
        const char *mid = text + text_len / 2;
        if (strncmp(text, mid, 50) == 0 && count < max_findings) {
            hunt_finding_t *f = &findings[count++];
            snprintf(f->description, sizeof(f->description),
                    "Repetitive content pattern detected");
            f->type = HUNT_TYPE_ANOMALY;
            f->confidence = 0.65f;
            f->timestamp = (uint64_t)time(NULL);
            strcpy(f->evidence, "Repeated patterns may indicate confusion attack");
        }
    }
    
    return count;
}

/* ===== Main Hunt Function ===== */

shield_err_t threat_hunter_hunt(const char *text, hunt_result_t *result)
{
    if (!g_hunter.enabled || !text || !result) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(result, 0, sizeof(*result));
    result->status = HUNT_STATUS_RUNNING;
    
    uint64_t start_time = (uint64_t)time(NULL);
    size_t remaining = 32;
    
    /* IOC hunting */
    if (g_hunter.hunt_ioc) {
        size_t found = hunt_ioc(text, result->findings + result->findings_count, remaining);
        result->findings_count += found;
        remaining -= found;
    }
    
    /* Behavioral hunting */
    if (g_hunter.hunt_behavioral && remaining > 0) {
        size_t found = hunt_behavioral(text, result->findings + result->findings_count, remaining);
        result->findings_count += found;
        remaining -= found;
    }
    
    /* Anomaly hunting */
    if (g_hunter.hunt_anomaly && remaining > 0) {
        size_t found = hunt_anomaly(text, result->findings + result->findings_count, remaining);
        result->findings_count += found;
    }
    
    /* Calculate threat score */
    if (result->findings_count > 0) {
        float max_conf = 0;
        float sum_conf = 0;
        
        for (size_t i = 0; i < result->findings_count; i++) {
            if (result->findings[i].confidence > max_conf) {
                max_conf = result->findings[i].confidence;
            }
            sum_conf += result->findings[i].confidence;
        }
        
        result->threat_score = max_conf + 0.1f * (result->findings_count - 1);
        if (result->threat_score > 1.0f) result->threat_score = 1.0f;
        
        g_hunter.threats_found++;
    }
    
    result->duration_ms = ((uint64_t)time(NULL) - start_time) * 1000;
    result->status = HUNT_STATUS_COMPLETED;
    g_hunter.hunts_completed++;
    
    return SHIELD_OK;
}

/* ===== Quick Check (for inline use) ===== */

float threat_hunter_quick_check(const char *text)
{
    hunt_result_t result;
    if (threat_hunter_hunt(text, &result) != SHIELD_OK) {
        return 0.0f;
    }
    return result.threat_score;
}

/* ===== Statistics ===== */

void threat_hunter_get_stats(char *buffer, size_t buflen)
{
    if (!buffer || buflen == 0) return;
    
    snprintf(buffer, buflen,
        "ThreatHunter Statistics:\n"
        "  Status: %s\n"
        "  Hunts Completed: %llu\n"
        "  Threats Found: %llu\n"
        "  IOCs in Database: %zu\n"
        "  Behavioral Patterns: %zu\n"
        "  Sensitivity: %.2f\n",
        g_hunter.enabled ? "ENABLED" : "DISABLED",
        (unsigned long long)g_hunter.hunts_completed,
        (unsigned long long)g_hunter.threats_found,
        IOC_DATABASE_SIZE,
        NUM_BEHAVIORAL_PATTERNS,
        g_hunter.sensitivity);
}

/* ===== Configuration ===== */

void threat_hunter_set_sensitivity(float sensitivity)
{
    if (sensitivity >= 0.0f && sensitivity <= 1.0f) {
        g_hunter.sensitivity = sensitivity;
    }
}

void threat_hunter_enable_type(hunt_type_t type, bool enable)
{
    switch (type) {
        case HUNT_TYPE_IOC:
            g_hunter.hunt_ioc = enable;
            break;
        case HUNT_TYPE_BEHAVIORAL:
            g_hunter.hunt_behavioral = enable;
            break;
        case HUNT_TYPE_ANOMALY:
            g_hunter.hunt_anomaly = enable;
            break;
        default:
            break;
    }
}
