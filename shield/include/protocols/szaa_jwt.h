/**
 * @file szaa_jwt.h
 * @brief SENTINEL Shield JWT Authentication Module
 * 
 * JWT verification for the SZAA (Shield Zone Authentication and Authorization) protocol.
 * Supports HS256 and RS256 algorithms.
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#ifndef SZAA_JWT_H
#define SZAA_JWT_H

#include <stdbool.h>
#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

#define JWT_ALG_HS256   0x01
#define JWT_ALG_RS256   0x02

#define JWT_MAX_TOKEN_SIZE      8192
#define JWT_MAX_CLAIM_SIZE      1024
#define JWT_MAX_SECRET_SIZE     512
#define JWT_MAX_PUBKEY_SIZE     4096

#define JWT_ERR_SUCCESS         0
#define JWT_ERR_INVALID_TOKEN   -1
#define JWT_ERR_EXPIRED         -2
#define JWT_ERR_INVALID_SIG     -3
#define JWT_ERR_INVALID_ISS     -4
#define JWT_ERR_INVALID_AUD     -5
#define JWT_ERR_MALLOC          -6
#define JWT_ERR_DECODE          -7
#define JWT_ERR_NOT_INITIALIZED -8

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * @brief JWT configuration structure
 */
typedef struct {
    uint8_t algorithm;              /**< JWT_ALG_HS256 or JWT_ALG_RS256 */
    char    secret[JWT_MAX_SECRET_SIZE];     /**< HS256 secret (base64) */
    char    public_key[JWT_MAX_PUBKEY_SIZE]; /**< RS256 public key (PEM) */
    char    issuer[JWT_MAX_CLAIM_SIZE];      /**< Expected issuer (iss) */
    char    audience[JWT_MAX_CLAIM_SIZE];    /**< Expected audience (aud) */
    int     clock_skew_seconds;     /**< Allowed clock skew for exp/iat */
    bool    require_exp;            /**< Require expiration claim */
    bool    require_iat;            /**< Require issued-at claim */
} jwt_config_t;

/**
 * @brief JWT claims structure
 */
typedef struct {
    char    sub[JWT_MAX_CLAIM_SIZE];  /**< Subject (user ID) */
    char    iss[JWT_MAX_CLAIM_SIZE];  /**< Issuer */
    char    aud[JWT_MAX_CLAIM_SIZE];  /**< Audience */
    char    jti[JWT_MAX_CLAIM_SIZE];  /**< JWT ID */
    time_t  exp;                      /**< Expiration time */
    time_t  iat;                      /**< Issued at time */
    time_t  nbf;                      /**< Not before time */
    
    /* Custom claims (raw JSON) */
    char    raw_payload[JWT_MAX_TOKEN_SIZE]; /**< Raw JSON payload for custom claims */
} jwt_claims_t;

/* ============================================================================
 * API Functions
 * ============================================================================ */

/**
 * @brief Initialize JWT module with configuration
 * 
 * @param config Pointer to JWT configuration
 * @return JWT_ERR_SUCCESS on success, error code otherwise
 */
int jwt_init(const jwt_config_t *config);

/**
 * @brief Cleanup JWT module
 */
void jwt_cleanup(void);

/**
 * @brief Verify JWT token and extract claims
 * 
 * @param token JWT token string (including "Bearer " prefix is OK)
 * @param claims Pointer to claims structure to fill
 * @return JWT_ERR_SUCCESS on success, error code otherwise
 */
int jwt_verify(const char *token, jwt_claims_t *claims);

/**
 * @brief Get error message for JWT error code
 * 
 * @param error_code Error code from jwt_verify
 * @return Human-readable error message
 */
const char* jwt_strerror(int error_code);

/**
 * @brief Check if JWT module is initialized
 * 
 * @return true if initialized, false otherwise
 */
bool jwt_is_initialized(void);

/**
 * @brief Get claim value from raw payload by key
 * 
 * @param claims Pointer to claims structure
 * @param key Claim key to look up
 * @param value Buffer to store value
 * @param value_size Size of value buffer
 * @return JWT_ERR_SUCCESS on success, error code otherwise
 */
int jwt_get_claim(const jwt_claims_t *claims, const char *key, 
                  char *value, size_t value_size);

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

/**
 * @brief Base64URL decode
 * 
 * @param input Base64URL encoded string
 * @param input_len Length of input
 * @param output Output buffer
 * @param output_size Size of output buffer
 * @return Decoded length or -1 on error
 */
int jwt_base64url_decode(const char *input, size_t input_len,
                         uint8_t *output, size_t output_size);

#ifdef __cplusplus
}
#endif

#endif /* SZAA_JWT_H */
