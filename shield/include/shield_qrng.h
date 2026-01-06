/**
 * @file shield_qrng.h
 * @brief Quantum Random Number Generator API for Shield
 * 
 * Provides high-quality random numbers using quantum-inspired algorithms
 * or true quantum sources (via remote API).
 * 
 * Based on research from tsotchke/quantum_rng and Cisco QRNG API.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#ifndef SHIELD_QRNG_H
#define SHIELD_QRNG_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include "shield_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * @brief QRNG backend type
 */
typedef enum qrng_backend {
    QRNG_BACKEND_AUTO = 0,      /**< Best available (remote > simulated) */
    QRNG_BACKEND_SIMULATED,     /**< Local quantum simulation */
    QRNG_BACKEND_REMOTE,        /**< Remote API (Cisco/LUMII) */
    QRNG_BACKEND_HARDWARE,      /**< Direct hardware (future) */
    QRNG_BACKEND_SYSTEM,        /**< Fall back to OS CSPRNG */
} qrng_backend_t;

/**
 * @brief QRNG configuration
 */
typedef struct qrng_config {
    qrng_backend_t backend;             /**< Preferred backend */
    char           api_endpoint[256];   /**< Remote API endpoint URL */
    char           api_key[128];        /**< Remote API key */
    size_t         pool_size;           /**< Entropy pool size (bytes) */
    bool           fallback_enabled;    /**< Fallback to simulated on failure */
    uint32_t       refresh_interval_ms; /**< Pool refresh interval */
} qrng_config_t;

/**
 * @brief QRNG statistics
 */
typedef struct qrng_stats {
    uint64_t bytes_generated;    /**< Total bytes generated */
    uint64_t requests;           /**< Total generation requests */
    uint64_t remote_fetches;     /**< Remote API fetches */
    uint64_t fallbacks;          /**< Fallback to simulated count */
    float    estimated_entropy;  /**< Estimated entropy per byte (0-8 bits) */
    qrng_backend_t active_backend; /**< Currently active backend */
} qrng_stats_t;

/* ============================================================================
 * Core API
 * ============================================================================ */

/**
 * @brief Initialize QRNG subsystem
 * 
 * @param config Configuration (NULL for defaults)
 * @return SHIELD_OK on success
 */
shield_err_t shield_qrng_init(const qrng_config_t *config);

/**
 * @brief Shutdown QRNG subsystem
 */
void shield_qrng_shutdown(void);

/**
 * @brief Generate random bytes
 * 
 * @param buf Output buffer
 * @param len Number of bytes to generate
 * @return SHIELD_OK on success
 */
shield_err_t shield_qrng_bytes(void *buf, size_t len);

/**
 * @brief Generate random 64-bit integer
 * 
 * @return Random uint64_t
 */
uint64_t shield_qrng_u64(void);

/**
 * @brief Generate random 32-bit integer
 * 
 * @return Random uint32_t
 */
uint32_t shield_qrng_u32(void);

/**
 * @brief Generate random integer in range [0, max)
 * 
 * @param max Upper bound (exclusive)
 * @return Random value in [0, max)
 */
uint64_t shield_qrng_range(uint64_t max);

/**
 * @brief Generate random float in range [0.0, 1.0)
 * 
 * @return Random double
 */
double shield_qrng_float(void);

/* ============================================================================
 * Utilities
 * ============================================================================ */

/**
 * @brief Get current QRNG statistics
 * 
 * @param stats Output statistics structure
 */
void shield_qrng_get_stats(qrng_stats_t *stats);

/**
 * @brief Estimate entropy quality of last generation
 * 
 * @return Entropy estimate in bits per byte (0-8)
 */
float shield_qrng_entropy_quality(void);

/**
 * @brief Force refresh of entropy pool
 * 
 * @return SHIELD_OK on success
 */
shield_err_t shield_qrng_refresh_pool(void);

/**
 * @brief Get backend name as string
 * 
 * @param backend Backend type
 * @return String name
 */
const char *qrng_backend_name(qrng_backend_t backend);

/* ============================================================================
 * Convenience Macros
 * ============================================================================ */

/** Generate a random byte */
#define QRNG_BYTE() ((uint8_t)shield_qrng_u32())

/** Generate random bytes into buffer */
#define QRNG_FILL(buf, len) shield_qrng_bytes((buf), (len))

/** Generate random in range */
#define QRNG_RANGE(max) shield_qrng_range(max)

#ifdef __cplusplus
}
#endif

#endif /* SHIELD_QRNG_H */
