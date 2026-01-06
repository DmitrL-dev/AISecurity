/**
 * @file qrng_remote.c
 * @brief Remote QRNG API Backend
 * 
 * Integrations:
 * - Cisco Outshift QRNG API (primary)
 * - LUMII RQRNG (backup)
 * 
 * Both provide true quantum randomness via HTTP API.
 * 
 * Note: Full HTTP implementation requires libcurl or WinHTTP.
 * This version provides stubs with fallback to simulated QRNG.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_qrng.h"
#include "shield_string_safe.h"

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#endif

/* ============================================================================
 * Configuration
 * ============================================================================ */

/* Cisco QRNG API - https://outshift.cisco.com/qrng */
#define CISCO_QRNG_ENDPOINT  "https://qrng.outshift.cisco.com/api/v1/random"
#define CISCO_QRNG_MAX_BITS  100000  /* 100k bits/day free tier */

/* LUMII RQRNG - https://qrng.lumii.lv */
#define LUMII_QRNG_ENDPOINT  "https://qrng.lumii.lv/api/random"

/* Default settings */
#define DEFAULT_FETCH_SIZE   1024    /* Bytes per fetch */
#define MAX_RETRY_COUNT      3
#define FETCH_TIMEOUT_MS     5000

/* ============================================================================
 * Internal State
 * ============================================================================ */

typedef struct qrng_remote_state {
    bool        initialized;
    char        api_endpoint[256];
    char        api_key[128];
    uint64_t    bytes_fetched_today;
    uint64_t    last_fetch_time;
    
    /* Response buffer */
    uint8_t    *response_buf;
    size_t      response_len;
    size_t      response_cap;
} qrng_remote_state_t;

static qrng_remote_state_t g_remote = {0};

/* ============================================================================
 * HTTP Response Handler
 * ============================================================================ */

#ifndef _WIN32
/* libcurl write callback */
static size_t curl_write_cb(void *ptr, size_t size, size_t nmemb, void *userdata) {
    size_t total = size * nmemb;
    qrng_remote_state_t *state = (qrng_remote_state_t *)userdata;
    
    /* Resize buffer if needed */
    if (state->response_len + total > state->response_cap) {
        size_t new_cap = state->response_cap * 2;
        if (new_cap < state->response_len + total) {
            new_cap = state->response_len + total + 1024;
        }
        uint8_t *new_buf = realloc(state->response_buf, new_cap);
        if (!new_buf) return 0;
        state->response_buf = new_buf;
        state->response_cap = new_cap;
    }
    
    memcpy(state->response_buf + state->response_len, ptr, total);
    state->response_len += total;
    
    return total;
}
#endif

/* ============================================================================
 * Remote Fetch Implementation
 * ============================================================================ */

/**
 * @brief Fetch random bytes from remote QRNG API
 * 
 * @param buf Output buffer
 * @param len Number of bytes to fetch
 * @return SHIELD_OK on success
 */
shield_err_t qrng_remote_fetch(void *buf, size_t len) {
    if (!g_remote.initialized) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Build request URL */
    char url[512];
    snprintf(url, sizeof(url), "%s?bytes=%zu&format=binary",
             g_remote.api_endpoint, len);
    
#ifdef _WIN32
    /* Windows: Use WinHTTP */
    HINTERNET session = WinHttpOpen(L"Shield-QRNG/1.0",
                                     WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) {
        return SHIELD_ERR_NETWORK;
    }
    
    /* Parse URL */
    URL_COMPONENTS urlComp = {0};
    urlComp.dwStructSize = sizeof(urlComp);
    wchar_t host[256] = {0};
    wchar_t path[256] = {0};
    urlComp.lpszHostName = host;
    urlComp.dwHostNameLength = sizeof(host) / sizeof(wchar_t);
    urlComp.lpszUrlPath = path;
    urlComp.dwUrlPathLength = sizeof(path) / sizeof(wchar_t);
    
    /* Convert URL to wide string */
    wchar_t wurl[512];
    MultiByteToWideChar(CP_UTF8, 0, url, -1, wurl, 512);
    
    if (!WinHttpCrackUrl(wurl, 0, 0, &urlComp)) {
        WinHttpCloseHandle(session);
        return SHIELD_ERR_NETWORK;
    }
    
    HINTERNET connect = WinHttpConnect(session, host,
                                        urlComp.nPort, 0);
    if (!connect) {
        WinHttpCloseHandle(session);
        return SHIELD_ERR_NETWORK;
    }
    
    DWORD flags = (urlComp.nScheme == INTERNET_SCHEME_HTTPS) 
                  ? WINHTTP_FLAG_SECURE : 0;
    HINTERNET request = WinHttpOpenRequest(connect, L"GET", path,
                                            NULL, WINHTTP_NO_REFERER,
                                            WINHTTP_DEFAULT_ACCEPT_TYPES,
                                            flags);
    if (!request) {
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return SHIELD_ERR_NETWORK;
    }
    
    /* Add API key header if configured */
    if (g_remote.api_key[0]) {
        wchar_t auth_header[256];
        swprintf(auth_header, 256, L"Authorization: Bearer %hs", g_remote.api_key);
        WinHttpAddRequestHeaders(request, auth_header, -1,
                                  WINHTTP_ADDREQ_FLAG_ADD);
    }
    
    /* Send request */
    BOOL result = WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                      WINHTTP_NO_REQUEST_DATA, 0, 0, 0);
    if (!result) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return SHIELD_ERR_NETWORK;
    }
    
    result = WinHttpReceiveResponse(request, NULL);
    if (!result) {
        WinHttpCloseHandle(request);
        WinHttpCloseHandle(connect);
        WinHttpCloseHandle(session);
        return SHIELD_ERR_NETWORK;
    }
    
    /* Read response */
    DWORD bytes_read = 0;
    size_t total_read = 0;
    uint8_t *out = (uint8_t *)buf;
    
    while (total_read < len) {
        if (!WinHttpReadData(request, out + total_read,
                              (DWORD)(len - total_read), &bytes_read)) {
            break;
        }
        if (bytes_read == 0) break;
        total_read += bytes_read;
    }
    
    WinHttpCloseHandle(request);
    WinHttpCloseHandle(connect);
    WinHttpCloseHandle(session);
    
    if (total_read < len) {
        return SHIELD_ERR_NETWORK;
    }
    
    g_remote.bytes_fetched_today += len;
    return SHIELD_OK;
    
#else
    /* Linux/macOS: Use libcurl */
    CURL *curl = curl_easy_init();
    if (!curl) {
        return SHIELD_ERR_INTERNAL;
    }
    
    /* Reset response buffer */
    g_remote.response_len = 0;
    if (!g_remote.response_buf) {
        g_remote.response_buf = malloc(len + 1024);
        g_remote.response_cap = len + 1024;
    }
    
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &g_remote);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, FETCH_TIMEOUT_MS);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    
    /* Add API key header if configured */
    struct curl_slist *headers = NULL;
    if (g_remote.api_key[0]) {
        char auth[256];
        snprintf(auth, sizeof(auth), "Authorization: Bearer %s", g_remote.api_key);
        headers = curl_slist_append(headers, auth);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    }
    
    CURLcode res = curl_easy_perform(curl);
    
    if (headers) curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    
    if (res != CURLE_OK) {
        return SHIELD_ERR_NETWORK;
    }
    
    /* Copy to output buffer */
    size_t to_copy = g_remote.response_len < len ? g_remote.response_len : len;
    memcpy(buf, g_remote.response_buf, to_copy);
    
    if (to_copy < len) {
        return SHIELD_ERR_NETWORK;
    }
    
    g_remote.bytes_fetched_today += len;
    return SHIELD_OK;
#endif
}

/* ============================================================================
 * Public API
 * ============================================================================ */

/**
 * @brief Initialize remote QRNG backend
 */
shield_err_t qrng_remote_init(const char *endpoint, const char *api_key) {
    if (g_remote.initialized) {
        return SHIELD_OK;
    }
    
    memset(&g_remote, 0, sizeof(g_remote));
    
    /* Set endpoint */
    if (endpoint && endpoint[0]) {
        shield_strcopy_s(g_remote.api_endpoint, sizeof(g_remote.api_endpoint), endpoint);
    } else {
        /* Default to Cisco QRNG */
        shield_strcopy_s(g_remote.api_endpoint, sizeof(g_remote.api_endpoint), 
                         CISCO_QRNG_ENDPOINT);
    }
    
    /* Set API key */
    if (api_key && api_key[0]) {
        shield_strcopy_s(g_remote.api_key, sizeof(g_remote.api_key), api_key);
    }
    
#ifndef _WIN32
    /* Initialize libcurl */
    curl_global_init(CURL_GLOBAL_DEFAULT);
#endif
    
    g_remote.initialized = true;
    return SHIELD_OK;
}

/**
 * @brief Shutdown remote QRNG backend
 */
void qrng_remote_shutdown(void) {
    if (!g_remote.initialized) return;
    
    if (g_remote.response_buf) {
        free(g_remote.response_buf);
    }
    
#ifndef _WIN32
    curl_global_cleanup();
#endif
    
    memset(&g_remote, 0, sizeof(g_remote));
}

/**
 * @brief Check if remote backend is available
 */
bool qrng_remote_available(void) {
    return g_remote.initialized;
}

/**
 * @brief Get daily usage statistics
 */
uint64_t qrng_remote_bytes_today(void) {
    return g_remote.bytes_fetched_today;
}

/**
 * @brief Switch to backup endpoint (LUMII)
 */
void qrng_remote_use_backup(void) {
    shield_strcopy_s(g_remote.api_endpoint, sizeof(g_remote.api_endpoint),
                     LUMII_QRNG_ENDPOINT);
}
