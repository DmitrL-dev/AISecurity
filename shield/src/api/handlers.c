/*
 * SENTINEL Shield - API Handlers
 * 
 * REST API endpoint handlers
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_context.h"
#include "shield_zone.h"
#include "shield_rule.h"
#include "shield_api.h"
#include "shield_metrics.h"

/* GET /health */
void handler_health(const http_request_t *req, http_response_t *resp, void *ctx)
{
    (void)req; (void)ctx;
    api_response_json(resp, 200, "{\"status\": \"ok\", \"version\": \"" SHIELD_VERSION_STRING "\"}");
}

/* GET /metrics */
void handler_metrics(const http_request_t *req, http_response_t *resp, void *ctx)
{
    (void)req;
    shield_context_t *sctx = (shield_context_t *)ctx;
    
    /* Export Prometheus format */
    if (sctx && sctx->metrics) {
        char *metrics = metrics_export_prometheus(sctx->metrics);
        if (metrics) {
            resp->status_code = 200;
            strncpy(resp->content_type, "text/plain", sizeof(resp->content_type) - 1);
            resp->body = metrics;
            resp->body_len = strlen(metrics);
            return;
        }
    }
    
    api_response_error(resp, 500, "Metrics not available");
}

/* GET /zones */
void handler_list_zones(const http_request_t *req, http_response_t *resp, void *ctx)
{
    (void)req;
    shield_context_t *sctx = (shield_context_t *)ctx;
    
    if (!sctx || !sctx->zones) {
        api_response_json(resp, 200, "{\"zones\": []}");
        return;
    }
    
    /* Build JSON */
    char *json = malloc(8192);
    if (!json) {
        api_response_error(resp, 500, "Out of memory");
        return;
    }
    
    size_t pos = 0;
    pos += snprintf(json + pos, 8192 - pos, "{\"zones\": [");
    
    shield_zone_t *zone = sctx->zones->zones;
    bool first = true;
    while (zone && pos < 8000) {
        if (!first) json[pos++] = ',';
        first = false;
        
        pos += snprintf(json + pos, 8192 - pos,
            "{"
            "\"id\": %u,"
            "\"name\": \"%s\","
            "\"type\": \"%s\","
            "\"provider\": \"%s\","
            "\"enabled\": %s,"
            "\"requests_in\": %lu,"
            "\"requests_out\": %lu,"
            "\"blocked_in\": %lu,"
            "\"blocked_out\": %lu"
            "}",
            zone->id, zone->name,
            zone_type_to_string(zone->type),
            zone->provider,
            zone->enabled ? "true" : "false",
            (unsigned long)zone->requests_in,
            (unsigned long)zone->requests_out,
            (unsigned long)zone->blocked_in,
            (unsigned long)zone->blocked_out);
        
        zone = zone->next;
    }
    
    pos += snprintf(json + pos, 8192 - pos, "]}");
    
    api_response_json(resp, 200, json);
    free(json);
}

/* POST /evaluate */
void handler_evaluate(const http_request_t *req, http_response_t *resp, void *ctx)
{
    shield_context_t *sctx = (shield_context_t *)ctx;
    
    if (!sctx || !sctx->rules) {
        api_response_error(resp, 500, "Shield not initialized");
        return;
    }
    
    if (!req->body || req->body_len == 0) {
        api_response_error(resp, 400, "Request body required");
        return;
    }
    
    /* Parse JSON body (simple parser) */
    /* Expected: {"zone": "name", "direction": "input", "data": "..."} */
    char zone_name[64] = "";
    char direction_str[16] = "input";
    (void)direction_str; /* TODO: use for direction parsing */
    
    /* Extract zone */
    const char *zone_ptr = strstr(req->body, "\"zone\"");
    if (zone_ptr) {
        zone_ptr = strchr(zone_ptr, ':');
        if (zone_ptr) {
            zone_ptr = strchr(zone_ptr, '"');
            if (zone_ptr) {
                zone_ptr++;
                char *end = strchr(zone_ptr, '"');
                if (end) {
                    size_t len = end - zone_ptr;
                    if (len < sizeof(zone_name)) {
                        strncpy(zone_name, zone_ptr, len);
                    }
                }
            }
        }
    }
    
    /* Extract data */
    const char *data_ptr = strstr(req->body, "\"data\"");
    const char *data = "";
    size_t data_len = 0;
    if (data_ptr) {
        data_ptr = strchr(data_ptr, ':');
        if (data_ptr) {
            data_ptr = strchr(data_ptr, '"');
            if (data_ptr) {
                data_ptr++;
                char *end = strchr(data_ptr, '"');
                if (end) {
                    data = data_ptr;
                    data_len = end - data_ptr;
                }
            }
        }
    }
    
    /* Find zone */
    shield_zone_t *zone = zone_find_by_name(sctx->zones, zone_name);
    zone_type_t type = zone ? zone->type : ZONE_TYPE_UNKNOWN;
    uint32_t acl = zone ? zone->in_acl : 100;
    
    /* Evaluate */
    rule_verdict_t verdict = rule_evaluate(sctx->rules, acl, DIRECTION_INPUT,
                                           type, zone_name, data, data_len);
    
    /* Build response */
    char json[512];
    snprintf(json, sizeof(json),
        "{"
        "\"action\": \"%s\","
        "\"rule\": %u,"
        "\"reason\": \"%s\""
        "}",
        action_to_string(verdict.action),
        verdict.matched_rule ? verdict.matched_rule->number : 0,
        verdict.reason ? verdict.reason : "");
    
    api_response_json(resp, 200, json);
}

/* GET /stats */
void handler_stats(const http_request_t *req, http_response_t *resp, void *ctx)
{
    (void)req;
    shield_context_t *sctx = (shield_context_t *)ctx;
    
    uint64_t total_in = 0, total_out = 0;
    uint64_t blocked_in = 0, blocked_out = 0;
    uint32_t zone_count = 0;
    
    if (sctx && sctx->zones) {
        zone_count = sctx->zones->count;
        shield_zone_t *zone = sctx->zones->zones;
        while (zone) {
            total_in += zone->requests_in;
            total_out += zone->requests_out;
            blocked_in += zone->blocked_in;
            blocked_out += zone->blocked_out;
            zone = zone->next;
        }
    }
    
    char json[512];
    snprintf(json, sizeof(json),
        "{"
        "\"zones\": %u,"
        "\"requests_in\": %lu,"
        "\"requests_out\": %lu,"
        "\"blocked_in\": %lu,"
        "\"blocked_out\": %lu,"
        "\"total_requests\": %lu,"
        "\"total_blocked\": %lu"
        "}",
        zone_count,
        (unsigned long)total_in, (unsigned long)total_out,
        (unsigned long)blocked_in, (unsigned long)blocked_out,
        (unsigned long)(total_in + total_out),
        (unsigned long)(blocked_in + blocked_out));
    
    api_response_json(resp, 200, json);
}

/* Register all handlers */
shield_err_t register_api_handlers(api_server_t *server)
{
    shield_err_t err;
    
    err = api_add_route(server, HTTP_GET, "/health", handler_health);
    if (err != SHIELD_OK) return err;
    
    err = api_add_route(server, HTTP_GET, "/metrics", handler_metrics);
    if (err != SHIELD_OK) return err;
    
    err = api_add_route(server, HTTP_GET, "/zones", handler_list_zones);
    if (err != SHIELD_OK) return err;
    
    err = api_add_route(server, HTTP_POST, "/evaluate", handler_evaluate);
    if (err != SHIELD_OK) return err;
    
    err = api_add_route(server, HTTP_GET, "/stats", handler_stats);
    if (err != SHIELD_OK) return err;
    
    return SHIELD_OK;
}
