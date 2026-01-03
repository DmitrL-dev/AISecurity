/*
 * SENTINEL IMMUNE — Production Agent Core
 * 
 * Platform-independent agent with full error handling.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>

#ifdef _WIN32
    #include <windows.h>
    #include <intrin.h>
#else
    #include <unistd.h>
    #include <sys/stat.h>
    #include <sys/time.h>
    #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        #include <cpuid.h>
    #endif
#endif

#include "../include/immune.h"

/* ==================== Constants ==================== */

#define MAX_SCAN_SIZE       (1 << 20)   /* 1MB */
#define MAX_FILE_SIZE       (10 << 20)  /* 10MB */
#define PATTERN_BUFFER      4096

/* Default patterns */
static const char *default_patterns[] = {
    "ignore all previous",
    "jailbreak",
    "dan mode",
    "bypass",
    "system prompt",
    "<script>",
    "meterpreter",
    "reverse_tcp",
    "union select",
    "${jndi:",
    NULL
};

/* ==================== CPU Feature Detection ==================== */

static void
detect_cpu_features(immune_agent_t *agent)
{
    agent->has_avx2 = 0;
    agent->has_sse42 = 0;
    agent->has_neon = 0;
    
#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
    #ifdef _WIN32
        int cpu_info[4];
        
        __cpuid(cpu_info, 1);
        agent->has_sse42 = (cpu_info[2] >> 20) & 1;
        
        __cpuidex(cpu_info, 7, 0);
        agent->has_avx2 = (cpu_info[1] >> 5) & 1;
    #else
        unsigned int eax, ebx, ecx, edx;
        
        if (__get_cpuid(1, &eax, &ebx, &ecx, &edx)) {
            agent->has_sse42 = (ecx >> 20) & 1;
        }
        
        if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx)) {
            agent->has_avx2 = (ebx >> 5) & 1;
        }
    #endif
#elif defined(__aarch64__) || defined(_M_ARM64)
    agent->has_neon = 1;  /* Always on ARM64 */
#endif
}

/* ==================== Timestamp ==================== */

uint64_t
immune_timestamp_ns(void)
{
#ifdef _WIN32
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (uint64_t)((counter.QuadPart * 1000000000ULL) / freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

/* ==================== Pattern Management ==================== */

int
immune_load_patterns(immune_agent_t *agent)
{
    if (!agent) {
        errno = EINVAL;
        return -1;
    }
    
    /* Clear existing */
    for (int i = 0; i < agent->pattern_count; i++) {
        if (agent->patterns[i].pattern) {
            free((void *)agent->patterns[i].pattern);
        }
    }
    agent->pattern_count = 0;
    
    /* Load defaults */
    for (int i = 0; default_patterns[i] != NULL && 
         agent->pattern_count < MAX_PATTERNS; i++) {
        
        size_t len = strlen(default_patterns[i]);
        char *pattern = malloc(len + 1);
        
        if (!pattern) {
            fprintf(stderr, "IMMUNE: Pattern allocation failed\n");
            continue;
        }
        
        memcpy(pattern, default_patterns[i], len + 1);
        
        agent->patterns[agent->pattern_count].pattern = pattern;
        agent->patterns[agent->pattern_count].length = len;
        agent->patterns[agent->pattern_count].level = 
            (i < 4) ? THREAT_CRITICAL : THREAT_HIGH;
        agent->patterns[agent->pattern_count].type = THREAT_TYPE_JAILBREAK;
        agent->patterns[agent->pattern_count].id = 1000 + i;
        
        agent->pattern_count++;
    }
    
    /* Try loading custom patterns */
    char path[512];
    snprintf(path, sizeof(path), "%s/patterns.txt", agent->data_path);
    
    FILE *fp = fopen(path, "r");
    if (fp) {
        char line[PATTERN_BUFFER];
        
        while (fgets(line, sizeof(line), fp) &&
               agent->pattern_count < MAX_PATTERNS) {
            
            /* Remove newline */
            size_t len = strlen(line);
            while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) {
                line[--len] = '\0';
            }
            
            if (len == 0 || line[0] == '#') continue;
            
            char *pattern = malloc(len + 1);
            if (!pattern) continue;
            
            memcpy(pattern, line, len + 1);
            
            agent->patterns[agent->pattern_count].pattern = pattern;
            agent->patterns[agent->pattern_count].length = len;
            agent->patterns[agent->pattern_count].level = THREAT_HIGH;
            agent->patterns[agent->pattern_count].type = THREAT_TYPE_INJECTION;
            agent->patterns[agent->pattern_count].id = 2000 + agent->pattern_count;
            
            agent->pattern_count++;
        }
        
        fclose(fp);
    }
    
    return agent->pattern_count;
}

int
immune_add_pattern(immune_agent_t *agent, const char *pattern,
                   threat_level_t level, threat_type_t type)
{
    if (!agent || !pattern) {
        errno = EINVAL;
        return -1;
    }
    
    if (agent->pattern_count >= MAX_PATTERNS) {
        errno = ENOSPC;
        return -1;
    }
    
    size_t len = strlen(pattern);
    if (len == 0 || len > PATTERN_BUFFER) {
        errno = EINVAL;
        return -1;
    }
    
    char *copy = malloc(len + 1);
    if (!copy) {
        return -1;
    }
    
    memcpy(copy, pattern, len + 1);
    
    int idx = agent->pattern_count++;
    agent->patterns[idx].pattern = copy;
    agent->patterns[idx].length = len;
    agent->patterns[idx].level = level;
    agent->patterns[idx].type = type;
    agent->patterns[idx].id = 3000 + idx;
    
    return idx;
}

/* ==================== Scanning ==================== */

/* Case-insensitive substring */
static const char*
strcasestr_impl(const char *haystack, size_t hlen,
                const char *needle, size_t nlen)
{
    if (nlen > hlen) return NULL;
    
    for (size_t i = 0; i <= hlen - nlen; i++) {
        int match = 1;
        
        for (size_t j = 0; j < nlen && match; j++) {
            char h = haystack[i + j];
            char n = needle[j];
            
            if (h >= 'A' && h <= 'Z') h += 32;
            if (n >= 'A' && n <= 'Z') n += 32;
            
            if (h != n) match = 0;
        }
        
        if (match) return haystack + i;
    }
    
    return NULL;
}

scan_result_t
immune_scan(immune_agent_t *agent, const void *data, size_t length)
{
    scan_result_t result = {0};
    
    if (!agent || !agent->initialized) {
        result.error = SCAN_ERR_NOT_INIT;
        return result;
    }
    
    if (!data || length == 0) {
        result.error = SCAN_ERR_INVALID;
        return result;
    }
    
    if (length > MAX_SCAN_SIZE) {
        length = MAX_SCAN_SIZE;
    }
    
    uint64_t start = immune_timestamp_ns();
    
    const char *text = (const char *)data;
    
    /* Pattern matching */
    for (int i = 0; i < agent->pattern_count; i++) {
        detection_pattern_t *pat = &agent->patterns[i];
        
        const char *match = strcasestr_impl(text, length,
                                            pat->pattern, pat->length);
        
        if (match) {
            if (pat->level > result.level) {
                result.detected = 1;
                result.level = pat->level;
                result.type = pat->type;
                result.pattern_id = pat->id;
                result.offset = (uint32_t)(match - text);
                result.length = (uint32_t)pat->length;
                result.confidence = 0.95f;
                
                /* Short-circuit on CRITICAL */
                if (result.level >= THREAT_CRITICAL) {
                    break;
                }
            }
        }
    }
    
    /* Innate layer (if available) */
    if (!result.detected || result.level < THREAT_HIGH) {
        threat_level_t innate = immune_innate_scan(text, length);
        if (innate > result.level) {
            result.detected = 1;
            result.level = innate;
            result.type = THREAT_TYPE_INJECTION;
            result.confidence = 0.8f;
        }
    }
    
    /* Check adaptive memory */
    if (!result.detected) {
        if (immune_memory_recall(agent, data, length)) {
            result.detected = 1;
            result.level = THREAT_HIGH;
            result.type = THREAT_TYPE_MALWARE;
            result.confidence = 1.0f;
        }
    }
    
    result.scan_time_ns = immune_timestamp_ns() - start;
    
    /* Update statistics */
    agent->stats.scans_total++;
    agent->stats.bytes_scanned += length;
    agent->stats.total_scan_time_ns += result.scan_time_ns;
    
    if (result.detected) {
        agent->stats.threats_detected++;
    }
    
    return result;
}

scan_result_t
immune_scan_file(immune_agent_t *agent, const char *path)
{
    scan_result_t result = {0};
    
    if (!agent || !path) {
        result.error = SCAN_ERR_INVALID;
        return result;
    }
    
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        result.error = SCAN_ERR_FILE;
        return result;
    }
    
    /* Get file size */
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    if (size <= 0) {
        fclose(fp);
        result.error = SCAN_ERR_FILE;
        return result;
    }
    
    if (size > MAX_FILE_SIZE) {
        size = MAX_FILE_SIZE;
    }
    
    /* Allocate buffer */
    uint8_t *buffer = malloc(size);
    if (!buffer) {
        fclose(fp);
        result.error = SCAN_ERR_MEMORY;
        return result;
    }
    
    /* Read file */
    size_t read_size = fread(buffer, 1, size, fp);
    fclose(fp);
    
    if (read_size == 0) {
        free(buffer);
        result.error = SCAN_ERR_FILE;
        return result;
    }
    
    /* Scan */
    result = immune_scan(agent, buffer, read_size);
    
    free(buffer);
    return result;
}

/* ==================== Initialization ==================== */

int
immune_init(immune_agent_t *agent, const char *data_path)
{
    if (!agent) {
        errno = EINVAL;
        return -1;
    }
    
    /* Clear structure */
    memset(agent, 0, sizeof(immune_agent_t));
    
    /* Set version */
    agent->version_major = IMMUNE_VERSION_MAJOR;
    agent->version_minor = IMMUNE_VERSION_MINOR;
    agent->version_patch = IMMUNE_VERSION_PATCH;
    
    /* Detect CPU features */
    detect_cpu_features(agent);
    
    /* Set data path */
    if (data_path) {
        strncpy(agent->data_path, data_path, sizeof(agent->data_path) - 1);
    } else {
#ifdef _WIN32
        strncpy(agent->data_path, "C:\\ProgramData\\immune",
                sizeof(agent->data_path) - 1);
#else
        strncpy(agent->data_path, "/var/immune",
                sizeof(agent->data_path) - 1);
#endif
    }
    
    /* Create data directory */
#ifdef _WIN32
    CreateDirectoryA(agent->data_path, NULL);
#else
    mkdir(agent->data_path, 0700);
#endif
    
    /* Load patterns */
    int patterns = immune_load_patterns(agent);
    if (patterns < 0) {
        fprintf(stderr, "IMMUNE: Failed to load patterns\n");
        return -1;
    }
    
    /* Load adaptive memory */
    immune_memory_load(agent);
    
    /* Mark initialized */
    agent->initialized = 1;
    agent->start_time = time(NULL);
    
    printf("IMMUNE: Agent initialized v%d.%d.%d\n",
           agent->version_major, agent->version_minor, agent->version_patch);
    printf("IMMUNE: Patterns: %d, Memory: %d entries\n",
           agent->pattern_count, agent->memory_count);
    printf("IMMUNE: CPU: AVX2=%d SSE4.2=%d NEON=%d\n",
           agent->has_avx2, agent->has_sse42, agent->has_neon);
    
    return 0;
}

void
immune_shutdown(immune_agent_t *agent)
{
    if (!agent || !agent->initialized) return;
    
    /* Save memory */
    immune_memory_save(agent);
    
    /* Free patterns */
    for (int i = 0; i < agent->pattern_count; i++) {
        if (agent->patterns[i].pattern) {
            free((void *)agent->patterns[i].pattern);
        }
    }
    
    /* Print final stats */
    printf("IMMUNE: Shutdown - scans=%lu threats=%lu bytes=%lu\n",
           agent->stats.scans_total,
           agent->stats.threats_detected,
           agent->stats.bytes_scanned);
    
    agent->initialized = 0;
}

/* ==================== Status ==================== */

void
immune_print_status(immune_agent_t *agent)
{
    if (!agent) return;
    
    time_t now = time(NULL);
    time_t uptime = now - agent->start_time;
    
    printf("\n=== IMMUNE AGENT STATUS ===\n");
    printf("Version:     %d.%d.%d\n",
           agent->version_major, agent->version_minor, agent->version_patch);
    printf("Initialized: %s\n", agent->initialized ? "yes" : "no");
    printf("Uptime:      %ld seconds\n", uptime);
    printf("Data path:   %s\n", agent->data_path);
    printf("\nCapabilities:\n");
    printf("  AVX2:   %s\n", agent->has_avx2 ? "yes" : "no");
    printf("  SSE4.2: %s\n", agent->has_sse42 ? "yes" : "no");
    printf("  NEON:   %s\n", agent->has_neon ? "yes" : "no");
    printf("\nPatterns:    %d loaded\n", agent->pattern_count);
    printf("Memory:      %d entries\n", agent->memory_count);
    printf("\nStatistics:\n");
    printf("  Scans:     %lu\n", agent->stats.scans_total);
    printf("  Threats:   %lu\n", agent->stats.threats_detected);
    printf("  Bytes:     %lu\n", agent->stats.bytes_scanned);
    
    if (agent->stats.scans_total > 0) {
        double avg_us = (double)agent->stats.total_scan_time_ns /
                        (double)agent->stats.scans_total / 1000.0;
        printf("  Avg scan:  %.2f µs\n", avg_us);
    }
    
    printf("===========================\n\n");
}

agent_stats_t
immune_get_stats(immune_agent_t *agent)
{
    agent_stats_t empty = {0};
    return agent ? agent->stats : empty;
}
