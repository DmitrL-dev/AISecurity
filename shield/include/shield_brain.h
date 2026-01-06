/**
 * @file shield_brain.h
 * @brief Brain FFI Public Interface
 * 
 * Interface for connecting Shield C guards to Brain Python engines.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_BRAIN_H
#define SHIELD_BRAIN_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Engine Types
 * ============================================================================ */

/**
 * @brief Brain engine categories
 */
typedef enum {
    BRAIN_ENGINE_INJECTION,           /**< Prompt injection detection */
    BRAIN_ENGINE_JAILBREAK,           /**< Jailbreak attempt detection */
    BRAIN_ENGINE_RAG_POISONING,       /**< RAG poisoning detection */
    BRAIN_ENGINE_AGENT_MANIPULATION,  /**< Agent manipulation detection */
    BRAIN_ENGINE_TOOL_HIJACKING,      /**< Tool hijacking detection */
    BRAIN_ENGINE_MCP_ATTACK,          /**< MCP protocol attacks */
    BRAIN_ENGINE_PII,                 /**< PII detection */
    BRAIN_ENGINE_EXFILTRATION,        /**< Data exfiltration */
    BRAIN_ENGINE_ALL                  /**< Run all applicable engines */
} brain_engine_category_t;

/**
 * @brief Severity levels
 */
typedef enum {
    BRAIN_SEVERITY_NONE = 0,
    BRAIN_SEVERITY_LOW = 1,
    BRAIN_SEVERITY_MEDIUM = 2,
    BRAIN_SEVERITY_HIGH = 3,
    BRAIN_SEVERITY_CRITICAL = 4
} brain_severity_t;

/* ============================================================================
 * Result Types
 * ============================================================================ */

/**
 * @brief Single engine result
 */
typedef struct {
    bool detected;              /**< Threat detected */
    double confidence;          /**< Confidence score (0-1) */
    brain_severity_t severity;  /**< Severity level */
    const char *engine_name;    /**< Engine that detected (may be NULL) */
    const char *reason;         /**< Human-readable reason (may be NULL) */
    const char *attack_type;    /**< Attack classification (may be NULL) */
    double latency_ms;          /**< Engine execution time */
} brain_result_t;

/**
 * @brief Aggregate result from multiple engines
 */
typedef struct {
    bool any_detected;          /**< Any engine detected threat */
    double max_confidence;      /**< Highest confidence score */
    brain_severity_t max_severity; /**< Highest severity */
    size_t engines_run;         /**< Number of engines executed */
    size_t engines_triggered;   /**< Number of engines that triggered */
    double total_latency_ms;    /**< Total execution time */
    
    brain_result_t *results;    /**< Individual results */
    size_t result_count;        /**< Number of results */
} brain_aggregate_result_t;

/* ============================================================================
 * Lifecycle
 * ============================================================================ */

/**
 * @brief Initialize Brain FFI
 * 
 * @param python_home Path to Python installation (NULL for default)
 * @param brain_path Path to Brain module (NULL for default)
 * @return 0 on success, -1 on error
 */
int brain_ffi_init(const char *python_home, const char *brain_path);

/**
 * @brief Shutdown Brain FFI
 */
void brain_ffi_shutdown(void);

/**
 * @brief Check if Brain is available
 * 
 * @return true if Brain engines can be called
 */
bool brain_available(void);

/**
 * @brief Get Brain mode
 * 
 * @return "embedded" (Python), "http" (API fallback), or "stub" (no Brain)
 */
const char* brain_mode(void);

/* ============================================================================
 * Analysis
 * ============================================================================ */

/**
 * @brief Analyze input with specific engine category
 * 
 * @param input Input text to analyze
 * @param category Engine category to use
 * @param result Result structure (caller provides)
 * @return 0 on success
 */
int brain_ffi_analyze(
    const char *input,
    brain_engine_category_t category,
    brain_result_t *result
);

/**
 * @brief Analyze input with all engines
 * 
 * @param input Input text to analyze
 * @param result Aggregate result (caller provides)
 * @return 0 on success
 */
int brain_ffi_analyze_all(
    const char *input,
    brain_aggregate_result_t *result
);

/**
 * @brief Analyze with specific engine by name
 * 
 * @param input Input text
 * @param engine_name Full engine name (e.g., "injection_engine.InjectionEngine")
 * @param result Result structure
 * @return 0 on success
 */
int brain_ffi_analyze_engine(
    const char *input,
    const char *engine_name,
    brain_result_t *result
);

/* ============================================================================
 * Result Management
 * ============================================================================ */

/**
 * @brief Free aggregate result
 */
void brain_result_free(brain_aggregate_result_t *result);

/**
 * @brief Get severity as string
 */
const char* brain_severity_string(brain_severity_t severity);

/* ============================================================================
 * Engine Discovery
 * ============================================================================ */

/**
 * @brief Get number of available engines
 */
size_t brain_engine_count(void);

/**
 * @brief Get engine names
 * 
 * @param names Array to fill with engine names
 * @param max_count Maximum number of names
 * @return Actual number of names written
 */
size_t brain_engine_names(const char **names, size_t max_count);

/**
 * @brief Check if specific engine is available
 */
bool brain_engine_available(const char *engine_name);

/* ============================================================================
 * Configuration
 * ============================================================================ */

/**
 * @brief Brain FFI configuration
 */
typedef struct {
    int timeout_ms;             /**< Engine call timeout (default: 1000) */
    bool enable_caching;        /**< Cache results (default: false) */
    int cache_ttl_seconds;      /**< Cache TTL (default: 60) */
    bool use_http_fallback;     /**< Fall back to HTTP if Python fails */
    const char *http_endpoint;  /**< Brain API endpoint for fallback */
    int max_concurrent;         /**< Max concurrent engine calls (default: 4) */
} brain_ffi_config_t;

/**
 * @brief Default configuration
 */
#define BRAIN_FFI_CONFIG_DEFAULT { \
    .timeout_ms = 1000, \
    .enable_caching = false, \
    .cache_ttl_seconds = 60, \
    .use_http_fallback = true, \
    .http_endpoint = "http://localhost:8000", \
    .max_concurrent = 4 \
}

/**
 * @brief Set configuration
 */
int brain_ffi_configure(const brain_ffi_config_t *config);

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_BRAIN_H */
