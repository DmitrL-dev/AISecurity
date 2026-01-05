/**
 * @file test_sllm.c
 * @brief Unit tests for SLLM protocol
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "../include/protocols/sllm.h"

/* Test helper */
#define TEST(name) static void name(void)
#define RUN_TEST(name) do { printf("  Testing %s... ", #name); name(); printf("OK\n"); } while(0)

/* ========================================================================= */
/*                              TESTS                                         */
/* ========================================================================= */

TEST(test_sllm_status_str) {
    assert(strcmp(sllm_status_str(SLLM_STATUS_OK), "OK") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_BLOCKED_INGRESS), "BLOCKED_INGRESS") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_BLOCKED_EGRESS), "BLOCKED_EGRESS") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_LLM_ERROR), "LLM_ERROR") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_TIMEOUT), "TIMEOUT") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_NETWORK_ERROR), "NETWORK_ERROR") == 0);
    assert(strcmp(sllm_status_str(SLLM_STATUS_CONFIG_ERROR), "CONFIG_ERROR") == 0);
}

TEST(test_sllm_build_openai_body) {
    sllm_request_t req = {0};
    sllm_message_t msg = {0};
    
    strcpy(msg.role, "user");
    msg.content = "Hello";
    msg.content_len = 5;
    
    req.messages = &msg;
    req.message_count = 1;
    strcpy(req.model, "gpt-4");
    
    char *body = NULL;
    size_t body_len = 0;
    
    shield_err_t err = sllm_build_openai_body(&req, &body, &body_len);
    assert(err == SHIELD_OK);
    assert(body != NULL);
    assert(strstr(body, "\"model\":\"gpt-4\"") != NULL);
    assert(strstr(body, "\"role\":\"user\"") != NULL);
    assert(strstr(body, "\"content\":\"Hello\"") != NULL);
    
    free(body);
}

TEST(test_sllm_build_gemini_body) {
    sllm_request_t req = {0};
    sllm_message_t msg = {0};
    
    strcpy(msg.role, "user");
    msg.content = "Test message";
    msg.content_len = 12;
    
    req.messages = &msg;
    req.message_count = 1;
    
    char *body = NULL;
    size_t body_len = 0;
    
    shield_err_t err = sllm_build_gemini_body(&req, &body, &body_len);
    assert(err == SHIELD_OK);
    assert(body != NULL);
    assert(strstr(body, "\"contents\"") != NULL);
    assert(strstr(body, "\"parts\"") != NULL);
    
    free(body);
}

TEST(test_sllm_init_shutdown) {
    sllm_config_t config = {0};
    config.provider_count = 1;
    config.active_provider = 0;
    config.ingress_enabled = true;
    config.egress_enabled = true;
    
    config.providers[0].provider = SLLM_PROVIDER_OPENAI;
    strcpy(config.providers[0].endpoint, "https://api.openai.com/v1/chat/completions");
    config.providers[0].enabled = true;
    
    shield_err_t err = sllm_init(&config);
    assert(err == SHIELD_OK);
    
    sllm_shutdown();
}

TEST(test_sllm_parse_openai_response) {
    const char *raw = "{\"choices\":[{\"message\":{\"content\":\"Hello from GPT!\"}}]}";
    char *content = NULL;
    size_t content_len = 0;
    
    shield_err_t err = sllm_parse_openai_response(raw, &content, &content_len);
    assert(err == SHIELD_OK);
    assert(content != NULL);
    assert(strcmp(content, "Hello from GPT!") == 0);
    
    free(content);
}

TEST(test_sllm_parse_gemini_response) {
    const char *raw = "{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"Hello from Gemini!\"}]}}]}";
    char *content = NULL;
    size_t content_len = 0;
    
    shield_err_t err = sllm_parse_gemini_response(raw, &content, &content_len);
    assert(err == SHIELD_OK);
    assert(content != NULL);
    assert(strcmp(content, "Hello from Gemini!") == 0);
    
    free(content);
}

TEST(test_sllm_response_free) {
    sllm_response_t resp = {0};
    resp.response_content = strdup("test");
    resp.ingress_analysis.detected_threats = strdup("[]");
    
    sllm_response_free(&resp);
    
    /* Should not crash and should be zeroed */
    assert(resp.response_content == NULL);
}

/* ========================================================================= */
/*                              MAIN                                          */
/* ========================================================================= */

int main(void) {
    printf("\n=== SLLM Protocol Unit Tests ===\n\n");
    
    RUN_TEST(test_sllm_status_str);
    RUN_TEST(test_sllm_build_openai_body);
    RUN_TEST(test_sllm_build_gemini_body);
    RUN_TEST(test_sllm_init_shutdown);
    RUN_TEST(test_sllm_parse_openai_response);
    RUN_TEST(test_sllm_parse_gemini_response);
    RUN_TEST(test_sllm_response_free);
    
    printf("\n=== All SLLM tests passed! ===\n\n");
    return 0;
}
