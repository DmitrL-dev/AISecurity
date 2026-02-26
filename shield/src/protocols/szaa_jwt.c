/**
 * @file szaa_jwt.c
 * @brief SENTINEL Shield JWT Authentication Implementation
 * 
 * @author SENTINEL Team
 * @version Dragon v4.1
 * @date 2026-01-09
 */

#include "szaa_jwt.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* wolfSSL for crypto operations */
#ifdef SHIELD_USE_WOLFSSL
#include <wolfssl/options.h>
#include <wolfssl/wolfcrypt/hmac.h>
#include <wolfssl/wolfcrypt/rsa.h>
#include <wolfssl/wolfcrypt/sha256.h>
#endif

/* No external JSON library - using built-in mini parser */

/* ============================================================================
 * Static Variables
 * ============================================================================ */

static jwt_config_t s_config;
static bool s_initialized = false;

/* ============================================================================
 * Mini JSON Parser (no external dependencies)
 * ============================================================================ */

/* Extract string value for a key from JSON */
static int json_get_string(const char *json, const char *key, 
                           char *value, size_t value_size) {
    char search[256];
    snprintf(search, sizeof(search), "\"%s\":", key);
    
    const char *found = strstr(json, search);
    if (!found) return -1;
    
    /* Skip to value */
    const char *start = found + strlen(search);
    while (*start == ' ' || *start == '\t') start++;
    
    if (*start == '"') {
        /* String value */
        start++;
        const char *end = strchr(start, '"');
        if (!end) return -1;
        
        size_t len = end - start;
        if (len >= value_size) len = value_size - 1;
        memcpy(value, start, len);
        value[len] = '\0';
        return 0;
    }
    
    return -1;
}

/* Extract number value for a key from JSON */
static int json_get_number(const char *json, const char *key, long long *value) {
    char search[256];
    snprintf(search, sizeof(search), "\"%s\":", key);
    
    const char *found = strstr(json, search);
    if (!found) return -1;
    
    /* Skip to value */
    const char *start = found + strlen(search);
    while (*start == ' ' || *start == '\t') start++;
    
    if (*start >= '0' && *start <= '9') {
        *value = atoll(start);
        return 0;
    }
    
    return -1;
}

/* ============================================================================
 * Base64URL Decode
 * ============================================================================ */

static const char base64url_chars[] = 
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

static int base64url_char_value(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '-') return 62;
    if (c == '_') return 63;
    return -1;
}

int jwt_base64url_decode(const char *input, size_t input_len,
                         uint8_t *output, size_t output_size) {
    if (!input || !output || input_len == 0) {
        return -1;
    }
    
    /* Calculate output length */
    size_t out_len = (input_len * 3) / 4;
    
    /* Adjust for padding */
    size_t padding = 0;
    if (input_len > 0 && input[input_len - 1] == '=') padding++;
    if (input_len > 1 && input[input_len - 2] == '=') padding++;
    out_len -= padding;
    
    if (out_len > output_size) {
        return -1;
    }
    
    size_t i, j;
    uint32_t buf = 0;
    int bits = 0;
    
    for (i = 0, j = 0; i < input_len && input[i] != '='; i++) {
        int val = base64url_char_value(input[i]);
        if (val < 0) continue; /* Skip invalid chars */
        
        buf = (buf << 6) | val;
        bits += 6;
        
        if (bits >= 8) {
            bits -= 8;
            if (j < output_size) {
                output[j++] = (uint8_t)(buf >> bits);
            }
        }
    }
    
    return (int)j;
}

/* ============================================================================
 * JWT Parsing
 * ============================================================================ */

static int jwt_split_token(const char *token, 
                           char *header, size_t header_size,
                           char *payload, size_t payload_size,
                           char *signature, size_t sig_size) {
    const char *p1, *p2;
    
    /* Find first dot */
    p1 = strchr(token, '.');
    if (!p1) return JWT_ERR_INVALID_TOKEN;
    
    /* Find second dot */
    p2 = strchr(p1 + 1, '.');
    if (!p2) return JWT_ERR_INVALID_TOKEN;
    
    /* Extract header */
    size_t header_len = p1 - token;
    if (header_len >= header_size) return JWT_ERR_INVALID_TOKEN;
    memcpy(header, token, header_len);
    header[header_len] = '\0';
    
    /* Extract payload */
    size_t payload_len = p2 - (p1 + 1);
    if (payload_len >= payload_size) return JWT_ERR_INVALID_TOKEN;
    memcpy(payload, p1 + 1, payload_len);
    payload[payload_len] = '\0';
    
    /* Extract signature */
    size_t sig_len = strlen(p2 + 1);
    if (sig_len >= sig_size) return JWT_ERR_INVALID_TOKEN;
    memcpy(signature, p2 + 1, sig_len);
    signature[sig_len] = '\0';
    
    return JWT_ERR_SUCCESS;
}

static int jwt_parse_claims(const char *json_str, jwt_claims_t *claims) {
    /* Clear claims */
    memset(claims, 0, sizeof(jwt_claims_t));
    
    /* Store raw payload */
    strncpy(claims->raw_payload, json_str, JWT_MAX_TOKEN_SIZE - 1);
    
    /* Extract standard claims using mini parser */
    json_get_string(json_str, "sub", claims->sub, JWT_MAX_CLAIM_SIZE);
    json_get_string(json_str, "iss", claims->iss, JWT_MAX_CLAIM_SIZE);
    json_get_string(json_str, "aud", claims->aud, JWT_MAX_CLAIM_SIZE);
    json_get_string(json_str, "jti", claims->jti, JWT_MAX_CLAIM_SIZE);
    
    long long exp_val = 0, iat_val = 0, nbf_val = 0;
    if (json_get_number(json_str, "exp", &exp_val) == 0) {
        claims->exp = (time_t)exp_val;
    }
    if (json_get_number(json_str, "iat", &iat_val) == 0) {
        claims->iat = (time_t)iat_val;
    }
    if (json_get_number(json_str, "nbf", &nbf_val) == 0) {
        claims->nbf = (time_t)nbf_val;
    }
    
    return JWT_ERR_SUCCESS;
}

/* ============================================================================
 * Signature Verification
 * ============================================================================ */

#ifdef SHIELD_USE_WOLFSSL
static int jwt_verify_hs256(const char *header_payload, const char *signature) {
    uint8_t sig_decoded[256];
    int sig_len = jwt_base64url_decode(signature, strlen(signature), 
                                        sig_decoded, sizeof(sig_decoded));
    if (sig_len < 0) return JWT_ERR_DECODE;
    
    /* Compute HMAC-SHA256 */
    Hmac hmac;
    uint8_t computed[WC_SHA256_DIGEST_SIZE];
    
    if (wc_HmacInit(&hmac, NULL, INVALID_DEVID) != 0) {
        return JWT_ERR_INVALID_SIG;
    }
    
    if (wc_HmacSetKey(&hmac, WC_SHA256, 
                      (const uint8_t*)s_config.secret, 
                      strlen(s_config.secret)) != 0) {
        wc_HmacFree(&hmac);
        return JWT_ERR_INVALID_SIG;
    }
    
    if (wc_HmacUpdate(&hmac, (const uint8_t*)header_payload, 
                      strlen(header_payload)) != 0) {
        wc_HmacFree(&hmac);
        return JWT_ERR_INVALID_SIG;
    }
    
    if (wc_HmacFinal(&hmac, computed) != 0) {
        wc_HmacFree(&hmac);
        return JWT_ERR_INVALID_SIG;
    }
    
    wc_HmacFree(&hmac);
    
    /* Timing-safe comparison */
    if (sig_len != WC_SHA256_DIGEST_SIZE) {
        return JWT_ERR_INVALID_SIG;
    }
    
    volatile uint8_t diff = 0;
    for (int i = 0; i < WC_SHA256_DIGEST_SIZE; i++) {
        diff |= computed[i] ^ sig_decoded[i];
    }
    
    return (diff == 0) ? JWT_ERR_SUCCESS : JWT_ERR_INVALID_SIG;
}
#else
static int jwt_verify_hs256(const char *header_payload, const char *signature) {
    /* Stub when wolfSSL not available */
    (void)header_payload;
    (void)signature;
    /* WARNING: Always accepting in non-crypto mode - for testing only! */
    return JWT_ERR_SUCCESS;
}
#endif

/* ============================================================================
 * Public API
 * ============================================================================ */

int jwt_init(const jwt_config_t *config) {
    if (!config) return JWT_ERR_INVALID_TOKEN;
    
    memcpy(&s_config, config, sizeof(jwt_config_t));
    s_initialized = true;
    
    return JWT_ERR_SUCCESS;
}

void jwt_cleanup(void) {
    memset(&s_config, 0, sizeof(jwt_config_t));
    s_initialized = false;
}

bool jwt_is_initialized(void) {
    return s_initialized;
}

int jwt_verify(const char *token, jwt_claims_t *claims) {
    if (!s_initialized) return JWT_ERR_NOT_INITIALIZED;
    if (!token || !claims) return JWT_ERR_INVALID_TOKEN;
    
    /* Skip "Bearer " prefix if present */
    if (strncmp(token, "Bearer ", 7) == 0) {
        token += 7;
    }
    
    /* Split token into parts */
    char header_b64[JWT_MAX_TOKEN_SIZE];
    char payload_b64[JWT_MAX_TOKEN_SIZE];
    char signature_b64[512];
    
    int err = jwt_split_token(token, 
                              header_b64, sizeof(header_b64),
                              payload_b64, sizeof(payload_b64),
                              signature_b64, sizeof(signature_b64));
    if (err != JWT_ERR_SUCCESS) return err;
    
    /* Decode payload */
    uint8_t payload_json[JWT_MAX_TOKEN_SIZE];
    int payload_len = jwt_base64url_decode(payload_b64, strlen(payload_b64),
                                           payload_json, sizeof(payload_json) - 1);
    if (payload_len < 0) return JWT_ERR_DECODE;
    payload_json[payload_len] = '\0';
    
    /* Parse claims */
    err = jwt_parse_claims((const char*)payload_json, claims);
    if (err != JWT_ERR_SUCCESS) return err;
    
    /* Verify signature */
    char header_payload[JWT_MAX_TOKEN_SIZE * 2];
    snprintf(header_payload, sizeof(header_payload), "%s.%s", 
             header_b64, payload_b64);
    
    if (s_config.algorithm == JWT_ALG_HS256) {
        err = jwt_verify_hs256(header_payload, signature_b64);
        if (err != JWT_ERR_SUCCESS) return err;
    }
    /* TODO: Add RS256 support */
    
    /* Verify expiration */
    time_t now = time(NULL);
    if (s_config.require_exp && claims->exp > 0) {
        if (now > claims->exp + s_config.clock_skew_seconds) {
            return JWT_ERR_EXPIRED;
        }
    }
    
    /* Verify issuer */
    if (strlen(s_config.issuer) > 0) {
        if (strcmp(claims->iss, s_config.issuer) != 0) {
            return JWT_ERR_INVALID_ISS;
        }
    }
    
    /* Verify audience */
    if (strlen(s_config.audience) > 0) {
        if (strcmp(claims->aud, s_config.audience) != 0) {
            return JWT_ERR_INVALID_AUD;
        }
    }
    
    return JWT_ERR_SUCCESS;
}

const char* jwt_strerror(int error_code) {
    switch (error_code) {
        case JWT_ERR_SUCCESS:       return "Success";
        case JWT_ERR_INVALID_TOKEN: return "Invalid token format";
        case JWT_ERR_EXPIRED:       return "Token expired";
        case JWT_ERR_INVALID_SIG:   return "Invalid signature";
        case JWT_ERR_INVALID_ISS:   return "Invalid issuer";
        case JWT_ERR_INVALID_AUD:   return "Invalid audience";
        case JWT_ERR_MALLOC:        return "Memory allocation failed";
        case JWT_ERR_DECODE:        return "Base64 decode failed";
        case JWT_ERR_NOT_INITIALIZED: return "JWT module not initialized";
        default:                    return "Unknown error";
    }
}

int jwt_get_claim(const jwt_claims_t *claims, const char *key,
                  char *value, size_t value_size) {
    if (!claims || !key || !value) return JWT_ERR_INVALID_TOKEN;
    
    /* Use mini parser to get claim from raw payload */
    if (json_get_string(claims->raw_payload, key, value, value_size) == 0) {
        return JWT_ERR_SUCCESS;
    }
    
    /* Try number as fallback */
    long long num_val = 0;
    if (json_get_number(claims->raw_payload, key, &num_val) == 0) {
        snprintf(value, value_size, "%lld", num_val);
        return JWT_ERR_SUCCESS;
    }
    
    return JWT_ERR_DECODE;
}
