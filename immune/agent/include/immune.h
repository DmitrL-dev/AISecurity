/*
 * SENTINEL IMMUNE — Production Agent Header
 * 
 * Complete platform-independent API.
 */

#ifndef IMMUNE_AGENT_H
#define IMMUNE_AGENT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>
#include <time.h>

/* ==================== Version ==================== */

#define IMMUNE_VERSION_MAJOR    0
#define IMMUNE_VERSION_MINOR    9
#define IMMUNE_VERSION_PATCH    0
#define IMMUNE_VERSION_STRING   "0.9.0"

/* ==================== Limits ==================== */

#define MAX_PATTERNS        1000
#define MAX_MEMORY_ENTRIES  10000
#define MAX_DATA_PATH       256

/* ==================== Platform Detection ==================== */

#if defined(_WIN32) || defined(_WIN64)
    #define IMMUNE_PLATFORM_WINDOWS    1
    #define IMMUNE_PLATFORM_NAME       "Windows"
#elif defined(__DragonFly__)
    #define IMMUNE_PLATFORM_DRAGONFLY  1
    #define IMMUNE_PLATFORM_NAME       "DragonFlyBSD"
#elif defined(__FreeBSD__)
    #define IMMUNE_PLATFORM_FREEBSD    1
    #define IMMUNE_PLATFORM_NAME       "FreeBSD"
#elif defined(__linux__)
    #define IMMUNE_PLATFORM_LINUX      1
    #define IMMUNE_PLATFORM_NAME       "Linux"
#elif defined(__APPLE__)
    #define IMMUNE_PLATFORM_MACOS      1
    #define IMMUNE_PLATFORM_NAME       "macOS"
#else
    #define IMMUNE_PLATFORM_UNKNOWN    1
    #define IMMUNE_PLATFORM_NAME       "Unknown"
#endif

/* ==================== Threat Levels ==================== */

typedef enum {
    THREAT_NONE = 0,
    THREAT_LOW = 1,
    THREAT_MEDIUM = 2,
    THREAT_HIGH = 3,
    THREAT_CRITICAL = 4
} threat_level_t;

/* ==================== Threat Types ==================== */

typedef enum {
    THREAT_TYPE_UNKNOWN = 0,
    THREAT_TYPE_JAILBREAK = 1,
    THREAT_TYPE_INJECTION = 2,
    THREAT_TYPE_MALWARE = 3,
    THREAT_TYPE_EXFIL = 4,
    THREAT_TYPE_LATERAL = 5,
    THREAT_TYPE_ENCODING = 6,
    THREAT_TYPE_HEURISTIC = 7
} threat_type_t;

/* ==================== Scan Errors ==================== */

typedef enum {
    SCAN_ERR_NONE = 0,
    SCAN_ERR_NOT_INIT = 1,
    SCAN_ERR_INVALID = 2,
    SCAN_ERR_MEMORY = 3,
    SCAN_ERR_FILE = 4,
    SCAN_ERR_TIMEOUT = 5
} scan_error_t;

/* ==================== Detection Pattern ==================== */

typedef struct {
    const char      *pattern;
    size_t          length;
    threat_level_t  level;
    threat_type_t   type;
    uint16_t        id;
} detection_pattern_t;

/* ==================== Memory Entry ==================== */

typedef struct {
    uint8_t         hash[32];       /* SHA-256 */
    threat_level_t  level;
    threat_type_t   type;
    time_t          first_seen;
    time_t          last_seen;
    uint32_t        hit_count;
    int             active;
} memory_entry_t;

/* ==================== Scan Result ==================== */

typedef struct {
    int             detected;       /* 0 = clean, 1 = threat */
    threat_level_t  level;
    threat_type_t   type;
    uint16_t        pattern_id;
    uint32_t        offset;         /* Position in data */
    uint32_t        length;         /* Match length */
    float           confidence;     /* 0.0 - 1.0 */
    uint64_t        scan_time_ns;
    scan_error_t    error;
} scan_result_t;

/* ==================== Agent Statistics ==================== */

typedef struct {
    uint64_t        scans_total;
    uint64_t        threats_detected;
    uint64_t        bytes_scanned;
    uint64_t        total_scan_time_ns;
    uint64_t        memory_hits;
    uint64_t        pattern_matches;
} agent_stats_t;

/* ==================== Agent Context ==================== */

typedef struct {
    /* Version */
    uint8_t         version_major;
    uint8_t         version_minor;
    uint8_t         version_patch;
    
    /* State */
    int             initialized;
    time_t          start_time;
    
    /* Paths */
    char            data_path[MAX_DATA_PATH];
    
    /* CPU capabilities */
    int             has_avx2;
    int             has_avx512;
    int             has_sse42;
    int             has_neon;
    
    /* Patterns */
    detection_pattern_t patterns[MAX_PATTERNS];
    int             pattern_count;
    
    /* Adaptive memory */
    memory_entry_t  memory[MAX_MEMORY_ENTRIES];
    int             memory_count;
    
    /* Statistics */
    agent_stats_t   stats;
} immune_agent_t;

/* ==================== Core API ==================== */

/* Initialization */
int     immune_init(immune_agent_t *agent, const char *data_path);
void    immune_shutdown(immune_agent_t *agent);

/* Pattern management */
int     immune_load_patterns(immune_agent_t *agent);
int     immune_add_pattern(immune_agent_t *agent, const char *pattern,
                           threat_level_t level, threat_type_t type);

/* Scanning */
scan_result_t immune_scan(immune_agent_t *agent, 
                          const void *data, size_t length);
scan_result_t immune_scan_file(immune_agent_t *agent, const char *path);

/* Innate layer */
threat_level_t immune_innate_scan(const char *data, size_t length);
scan_result_t immune_innate_scan_full(const char *data, size_t length);

/* Adaptive memory */
int     immune_memory_learn(immune_agent_t *agent, 
                            const void *data, size_t length);
int     immune_memory_recall(immune_agent_t *agent,
                             const void *data, size_t length);
int     immune_memory_save(immune_agent_t *agent);
int     immune_memory_load(immune_agent_t *agent);

/* Statistics */
void    immune_print_status(immune_agent_t *agent);
agent_stats_t immune_get_stats(immune_agent_t *agent);

/* Utilities */
uint64_t immune_timestamp_ns(void);

/* ==================== SIMD API ==================== */

#ifdef __x86_64__
int     immune_simd_scan_avx2(const char *data, size_t length,
                              const char **patterns, int pattern_count);
int     immune_simd_scan_sse42(const char *data, size_t length,
                               const char *pattern, size_t pattern_len);
#endif

/* ==================== Hive Communication ==================== */

int     immune_hive_connect(const char *host, uint16_t port);
void    immune_hive_disconnect(void);
int     immune_hive_register(immune_agent_t *agent);
int     immune_hive_heartbeat(void);
int     immune_hive_report_threat(scan_result_t *result, 
                                  const char *context);

#ifdef __cplusplus
}
#endif

#endif /* IMMUNE_AGENT_H */
