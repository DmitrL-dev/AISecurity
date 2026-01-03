/*
 * SENTINEL IMMUNE — Production Hive Core Header
 * 
 * Complete structure definitions and API.
 */

#ifndef IMMUNE_HIVE_H
#define IMMUNE_HIVE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <time.h>
#include <pthread.h>

/* ==================== Version ==================== */

#define HIVE_VERSION_MAJOR      0
#define HIVE_VERSION_MINOR      9
#define HIVE_VERSION_PATCH      0
#define HIVE_VERSION_STRING     "0.9.0"
#define HIVE_VERSION            HIVE_VERSION_STRING

/* ==================== Limits ==================== */

#define MAX_AGENTS              1024
#define MAX_THREATS             10000
#define MAX_SIGNATURES          5000
#define MAX_PEERS               50
#define HEARTBEAT_TIMEOUT       120
#define MAX_HOSTNAME            256
#define MAX_IP_LEN              64
#define MAX_SCAN_THREADS        16

/* ==================== Threat Levels ==================== */

typedef enum {
    THREAT_LEVEL_NONE = 0,
    THREAT_LEVEL_LOW = 1,
    THREAT_LEVEL_MEDIUM = 2,
    THREAT_LEVEL_HIGH = 3,
    THREAT_LEVEL_CRITICAL = 4
} threat_level_t;

/* ==================== Agent Status ==================== */

typedef enum {
    AGENT_STATUS_UNKNOWN = 0,
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OFFLINE,
    AGENT_STATUS_COMPROMISED,
    AGENT_STATUS_QUARANTINED,
    AGENT_STATUS_ISOLATED
} agent_status_t;

/* ==================== Threat Types ==================== */

typedef enum {
    THREAT_TYPE_UNKNOWN = 0,
    THREAT_TYPE_JAILBREAK,
    THREAT_TYPE_INJECTION,
    THREAT_TYPE_MALWARE,
    THREAT_TYPE_EXFIL,
    THREAT_TYPE_LATERAL,
    THREAT_TYPE_ENCODING
} threat_type_t;

/* ==================== Response Actions ==================== */

typedef enum {
    ACTION_NONE = 0,
    ACTION_LOG,
    ACTION_ALERT,
    ACTION_BLOCK,
    ACTION_ISOLATE,
    ACTION_KILL,
    ACTION_QUARANTINE
} response_action_t;

/* Backward compatibility aliases */
#define RESPONSE_LOG        ACTION_LOG
#define RESPONSE_ALERT      ACTION_ALERT
#define RESPONSE_BLOCK      ACTION_BLOCK
#define RESPONSE_ISOLATE    ACTION_ISOLATE
#define RESPONSE_KILL       ACTION_KILL
#define RESPONSE_QUARANTINE ACTION_QUARANTINE

/* ==================== Agent Registration ==================== */

typedef struct {
    uint32_t        agent_id;
    uint8_t         auth_token[32];
    
    char            hostname[MAX_HOSTNAME];
    char            ip_address[64];
    char            os_type[32];
    char            os_version[64];
    
    uint8_t         version_major;
    uint8_t         version_minor;
    uint8_t         version_patch;
    
    agent_status_t  status;
    int             active;
    
    time_t          registered_at;
    time_t          last_heartbeat;
    
    /* Capabilities */
    int             has_avx2;
    int             has_sse42;
    int             has_kernel_hooks;
    
    /* Statistics */
    uint64_t        threats_detected;
    uint64_t        scans_performed;
    uint64_t        bytes_scanned;
} immune_agent_t;

/* ==================== Threat Event ==================== */

typedef struct {
    uint64_t        event_id;
    uint32_t        agent_id;
    
    time_t          timestamp;
    threat_level_t  level;
    threat_type_t   type;
    
    char            signature[512];
    char            context[1024];
    char            source_file[256];
    uint32_t        source_line;
    
    response_action_t action;
    int             resolved;
} threat_event_t;

/* ==================== Signature ==================== */

typedef struct {
    uint32_t        sig_id;
    char            pattern[256];
    size_t          pattern_length;
    threat_level_t  level;
    threat_type_t   type;
    uint64_t        matches;
    time_t          added_at;
} immune_signature_t;

/* ==================== Hive Statistics ==================== */

typedef struct {
    uint32_t        agents_total;
    uint32_t        agents_online;
    uint32_t        agents_offline;
    uint32_t        agents_compromised;
    
    uint64_t        threats_total;
    uint64_t        threats_critical;
    uint64_t        threats_high;
    uint64_t        threats_medium;
    uint64_t        threats_low;
    
    uint64_t        signatures_total;
    uint64_t        api_requests;
    
    time_t          start_time;
    time_t          last_threat;
} hive_stats_t;

/* ==================== Hive Context ==================== */

typedef struct {
    /* Identity */
    char            hive_id[64];
    uint8_t         master_key[32];
    int             master_key_loaded;
    
    /* Configuration */
    uint16_t        api_port;
    uint16_t        agent_port;
    char            data_path[256];
    char            log_path[256];
    
    /* State */
    int             running;
    int             initialized;
    
    /* Agents */
    immune_agent_t  agents[MAX_AGENTS];
    pthread_mutex_t agents_lock;
    
    /* Threats */
    threat_event_t  threats[MAX_THREATS];
    int             threat_count;
    pthread_mutex_t threats_lock;
    
    /* Signatures */
    immune_signature_t signatures[MAX_SIGNATURES];
    int             signature_count;
    pthread_rwlock_t signatures_lock;
    
    /* Statistics */
    hive_stats_t    stats;
    
    /* Threads */
    pthread_t       api_thread;
    pthread_t       agent_thread;
    pthread_t       monitor_thread;
} immune_hive_t;

/* ==================== Core API ==================== */

/* Initialization */
int     hive_init(immune_hive_t *hive, const char *config_path);
void    hive_shutdown(immune_hive_t *hive);

/* Agent management */
uint32_t hive_register_agent(immune_hive_t *hive, const char *hostname,
                             const char *ip, const char *os_type);
int     hive_update_agent(immune_hive_t *hive, uint32_t agent_id,
                          agent_status_t status);
int     hive_agent_heartbeat(immune_hive_t *hive, uint32_t agent_id);
immune_agent_t* hive_get_agent(immune_hive_t *hive, uint32_t agent_id);

/* Threat handling */
uint64_t hive_report_threat(immune_hive_t *hive, threat_event_t *event);
int     hive_resolve_threat(immune_hive_t *hive, uint64_t event_id);
threat_event_t* hive_get_threat(immune_hive_t *hive, uint64_t event_id);

/* Signatures */
uint32_t hive_add_signature(immune_hive_t *hive, const char *pattern,
                            threat_level_t level, threat_type_t type);
int     hive_remove_signature(immune_hive_t *hive, uint32_t sig_id);

/* Persistence */
int     hive_save_state(immune_hive_t *hive);
int     hive_load_state(immune_hive_t *hive);

/* Status */
void    hive_print_status(immune_hive_t *hive);
hive_stats_t hive_get_stats(immune_hive_t *hive);

/* ==================== Network API ==================== */

int     network_start(immune_hive_t *hive);
void    network_stop(immune_hive_t *hive);

/* ==================== API Server ==================== */

int     api_start(immune_hive_t *hive);
void    api_stop(void);

/* ==================== Crypto API ==================== */

int     crypto_init(void);
void    crypto_shutdown(void);
int     crypto_random_bytes(uint8_t *buffer, size_t size);
int     crypto_sha256(const uint8_t *data, size_t len, uint8_t *hash);
int     crypto_aes_encrypt(const uint8_t *pt, size_t pt_len,
                           const uint8_t *key, const uint8_t *iv,
                           size_t iv_len, const uint8_t *aad,
                           size_t aad_len, uint8_t *ct, uint8_t *tag);
int     crypto_aes_decrypt(const uint8_t *ct, size_t ct_len,
                           const uint8_t *key, const uint8_t *iv,
                           size_t iv_len, const uint8_t *aad,
                           size_t aad_len, const uint8_t *tag,
                           uint8_t *pt);

/* ==================== Scheduler API ==================== */

typedef void (*task_callback_t)(void *arg);

int     scheduler_init(immune_hive_t *hive);
void    scheduler_shutdown(void);
uint32_t scheduler_add_task(const char *name, task_callback_t cb,
                            void *arg, int interval_sec);
int     scheduler_start(void);
void    scheduler_stop(void);

/* ==================== Deploy API ==================== */

int     deploy_init(const char *agent_path);
void    deploy_shutdown(void);
uint32_t deploy_add_credential(const char *username, const char *password,
                               int type, int priority);
uint32_t deploy_queue_target(const char *host, uint16_t port,
                             const char *os_type, uint32_t cred_id);
int     deploy_start(void);
void    deploy_stop(void);

/* ==================== Exploit API ==================== */

int     exploit_init(const char *storage_path, const uint8_t *key);
void    exploit_shutdown(void);
uint32_t exploit_add(const char *name, const char *cve, int category,
                     int platform, const uint8_t *payload,
                     size_t payload_size, int risk_level,
                     const char *description);
int     exploit_get_payload(uint32_t exploit_id, uint8_t **payload,
                            size_t *size);
void    exploit_release_payload(uint8_t *payload, size_t size);
int     exploit_save_all(void);
int     exploit_load_all(void);

/* ==================== HSM API ==================== */

typedef enum {
    HSM_NONE = 0,
    HSM_TPM2,
    HSM_YUBIHSM,
    HSM_CLOUDKMS,
    HSM_SOFTWARE
} hsm_provider_t;

int     hsm_init(hsm_provider_t provider);
void    hsm_shutdown(void);
int     hsm_seal(const char *name, const uint8_t *data, size_t size);
int     hsm_unseal(const char *name, uint8_t *data, size_t *size);
int     hsm_get_key(uint8_t *key, size_t size);

/* ==================== Alert API ==================== */

int     alert_init(const char *log_path);
void    alert_shutdown(void);
int     alert_send(int priority, const char *title, const char *message);
int     alert_threat(threat_level_t level, const char *details);

/* ==================== SOC API ==================== */

int     soc_init(void);
void    soc_shutdown(void);
int     soc_add_target(const char *host, uint16_t port, int format);
int     soc_send_threat(threat_event_t *event);

/* ==================== SENTINEL AI Bridge API ==================== */

int     sentinel_init(const char *host, uint16_t port, const char *api_key);
void    sentinel_shutdown(void);
int     sentinel_analyze(threat_event_t *event, void *verdict);
int     sentinel_queue_event(threat_event_t *event);
response_action_t sentinel_get_recommended_action(threat_event_t *event);

/* ==================== Correlation Engine API ==================== */

int     correlate_analyze(immune_hive_t *hive);
int     correlate_detect_lateral_movement(immune_hive_t *hive);
int     correlate_detect_exfiltration(immune_hive_t *hive);
void*   correlate_thread(void *arg);
void    correlate_clear(void);

/* ==================== Playbook Engine API ==================== */

int     playbook_init(void);
int     playbook_execute(immune_hive_t *hive, threat_event_t *event);
void    playbook_stats(void);

#ifdef __cplusplus
}
#endif

#endif /* IMMUNE_HIVE_H */
