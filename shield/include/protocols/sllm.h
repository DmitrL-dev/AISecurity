/**
 * @file sllm.h
 * @brief SENTINEL LLM Forward Proxy Protocol
 * 
 * Handles forwarding requests to LLM backends (OpenAI, Gemini, Anthropic)
 * with full ingress/egress security analysis via Brain.
 * 
 * @author SENTINEL Team
 * @version 1.0.0
 * @date January 2026
 */

#ifndef SENTINEL_SLLM_H
#define SENTINEL_SLLM_H

#include <stddef.h>
#include <stdbool.h>
#include "shield_common.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/*                              CONSTANTS                                     */
/* ========================================================================= */

#define SLLM_MAX_PROVIDERS      8
#define SLLM_MAX_URL_LEN        512
#define SLLM_MAX_API_KEY_LEN    256
#define SLLM_MAX_MODEL_LEN      64
#define SLLM_MAX_RESPONSE_LEN   (1024 * 1024)  /* 1MB max response */
#define SLLM_DEFAULT_TIMEOUT_MS 30000

/* ========================================================================= */
/*                              ENUMS                                         */
/* ========================================================================= */

/**
 * @brief Supported LLM providers
 */
typedef enum {
    SLLM_PROVIDER_OPENAI = 0,
    SLLM_PROVIDER_GEMINI,
    SLLM_PROVIDER_ANTHROPIC,
    SLLM_PROVIDER_OLLAMA,
    SLLM_PROVIDER_CUSTOM
} sllm_provider_t;

/**
 * @brief Proxy request/response status
 */
typedef enum {
    SLLM_STATUS_OK = 0,
    SLLM_STATUS_BLOCKED_INGRESS,
    SLLM_STATUS_BLOCKED_EGRESS,
    SLLM_STATUS_LLM_ERROR,
    SLLM_STATUS_TIMEOUT,
    SLLM_STATUS_NETWORK_ERROR,
    SLLM_STATUS_CONFIG_ERROR
} sllm_status_t;

/* ========================================================================= */
/*                              STRUCTURES                                    */
/* ========================================================================= */

/**
 * @brief LLM provider configuration
 */
typedef struct {
    sllm_provider_t provider;
    char endpoint[SLLM_MAX_URL_LEN];
    char api_key[SLLM_MAX_API_KEY_LEN];
    char default_model[SLLM_MAX_MODEL_LEN];
    int timeout_ms;
    bool enabled;
} sllm_provider_config_t;

/**
 * @brief SLLM module configuration
 */
typedef struct {
    sllm_provider_config_t providers[SLLM_MAX_PROVIDERS];
    int provider_count;
    int active_provider;  /* Index of active provider */
    bool ingress_enabled;
    bool egress_enabled;
    bool sanitize_response;
    char brain_endpoint[SLLM_MAX_URL_LEN];
    int brain_port;
} sllm_config_t;

/**
 * @brief Chat message structure
 */
typedef struct {
    char role[32];      /* "user", "assistant", "system" */
    char *content;      /* Message content (dynamically allocated) */
    size_t content_len;
} sllm_message_t;

/**
 * @brief Proxy request structure
 */
typedef struct {
    sllm_message_t *messages;
    int message_count;
    char model[SLLM_MAX_MODEL_LEN];
    char request_id[64];
    float temperature;
    int max_tokens;
} sllm_request_t;

/**
 * @brief Ingress/Egress analysis result
 */
typedef struct {
    bool allowed;
    float risk_score;
    char verdict_reason[256];
    char *detected_threats;  /* JSON array */
    char *anonymized_content;
    char *sanitized_response;
} sllm_analysis_t;

/**
 * @brief Proxy response structure
 */
typedef struct {
    sllm_status_t status;
    char *response_content;
    size_t response_len;
    sllm_analysis_t ingress_analysis;
    sllm_analysis_t egress_analysis;
    int llm_http_status;
    double latency_ms;
    char error_message[256];
} sllm_response_t;

/* ========================================================================= */
/*                              API FUNCTIONS                                 */
/* ========================================================================= */

/**
 * @brief Initialize SLLM module
 * @param config Configuration for SLLM
 * @return SHIELD_OK on success
 */
shield_err_t sllm_init(const sllm_config_t *config);

/**
 * @brief Shutdown SLLM module
 */
void sllm_shutdown(void);

/**
 * @brief Set active LLM provider
 * @param provider_index Index of provider to activate
 * @return SHIELD_OK on success
 */
shield_err_t sllm_set_provider(int provider_index);

/**
 * @brief Full proxy request: Ingress → LLM → Egress
 * 
 * @param request Input request with messages
 * @param response Output response (caller must free)
 * @return SHIELD_OK on success
 */
shield_err_t sllm_proxy_request(const sllm_request_t *request,
                                 sllm_response_t *response);

/**
 * @brief Ingress analysis only
 * @param content User message to analyze
 * @param analysis Output analysis result
 * @return SHIELD_OK on success
 */
shield_err_t sllm_analyze_ingress(const char *content,
                                   sllm_analysis_t *analysis);

/**
 * @brief Egress analysis only  
 * @param response LLM response to analyze
 * @param original_prompt Original user prompt (for context)
 * @param analysis Output analysis result
 * @return SHIELD_OK on success
 */
shield_err_t sllm_analyze_egress(const char *response,
                                  const char *original_prompt,
                                  sllm_analysis_t *analysis);

/**
 * @brief Forward request to LLM (without security analysis)
 * @param request Input request
 * @param response Raw LLM response
 * @param response_len Length of response
 * @return SHIELD_OK on success
 */
shield_err_t sllm_forward_to_llm(const sllm_request_t *request,
                                  char **response,
                                  size_t *response_len);

/**
 * @brief Free response resources
 * @param response Response to free
 */
void sllm_response_free(sllm_response_t *response);

/**
 * @brief Free request resources
 * @param request Request to free
 */
void sllm_request_free(sllm_request_t *request);

/**
 * @brief Get status string
 * @param status Status code
 * @return Human-readable status string
 */
const char *sllm_status_str(sllm_status_t status);

/* ========================================================================= */
/*                          PROVIDER HELPERS                                  */
/* ========================================================================= */

/**
 * @brief Build request body for OpenAI API
 */
shield_err_t sllm_build_openai_body(const sllm_request_t *req, 
                                     char **body, 
                                     size_t *body_len);

/**
 * @brief Build request body for Gemini API
 */
shield_err_t sllm_build_gemini_body(const sllm_request_t *req,
                                     char **body,
                                     size_t *body_len);

/**
 * @brief Build request body for Anthropic API
 */
shield_err_t sllm_build_anthropic_body(const sllm_request_t *req,
                                        char **body,
                                        size_t *body_len);

/**
 * @brief Parse OpenAI response
 */
shield_err_t sllm_parse_openai_response(const char *raw, 
                                         char **content,
                                         size_t *content_len);

/**
 * @brief Parse Gemini response
 */
shield_err_t sllm_parse_gemini_response(const char *raw,
                                         char **content,
                                         size_t *content_len);

/**
 * @brief Parse Anthropic response
 */
shield_err_t sllm_parse_anthropic_response(const char *raw,
                                            char **content,
                                            size_t *content_len);

#ifdef __cplusplus
}
#endif

#endif /* SENTINEL_SLLM_H */
