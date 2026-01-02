/*
 * SENTINEL Shield - Encoding Detector Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_encoding.h"
#include "shield_base64.h"

/* Check if all chars are hex */
static bool is_hex_string(const char *s, size_t len)
{
    if (len < 2 || len % 2 != 0) return false;
    
    for (size_t i = 0; i < len; i++) {
        if (!isxdigit((unsigned char)s[i])) return false;
    }
    return true;
}

/* Leetspeak mapping */
static char deleet(char c)
{
    switch (c) {
    case '0': return 'o';
    case '1': return 'i';
    case '3': return 'e';
    case '4': return 'a';
    case '5': return 's';
    case '7': return 't';
    case '@': return 'a';
    case '$': return 's';
    default: return c;
    }
}

/* Detect encoding */
shield_err_t detect_encoding(const char *text, size_t len, encoding_result_t *result)
{
    if (!text || !result) return SHIELD_ERR_INVALID;
    
    memset(result, 0, sizeof(*result));
    
    /* Check Base64 */
    if (base64_is_valid(text) && len >= 4 && len % 4 == 0) {
        result->types[result->type_count++] = ENCODING_BASE64;
        result->confidence += 0.8f;
    }
    
    /* Check Hex */
    if (is_hex_string(text, len)) {
        result->types[result->type_count++] = ENCODING_HEX;
        result->confidence += 0.7f;
    }
    
    /* Check URL encoding */
    if (strchr(text, '%') != NULL) {
        int percent_count = 0;
        for (size_t i = 0; i < len; i++) {
            if (text[i] == '%') percent_count++;
        }
        if (percent_count > len / 10) {
            result->types[result->type_count++] = ENCODING_URL;
            result->confidence += 0.6f;
        }
    }
    
    /* Check for HTML entities */
    if (strstr(text, "&amp;") || strstr(text, "&lt;") || 
        strstr(text, "&gt;") || strstr(text, "&#")) {
        result->types[result->type_count++] = ENCODING_HTML;
        result->confidence += 0.5f;
    }
    
    /* Check for Unicode escapes */
    if (strstr(text, "\\u") || strstr(text, "\\x")) {
        result->types[result->type_count++] = ENCODING_UNICODE_ESCAPE;
        result->confidence += 0.6f;
    }
    
    /* Check for leetspeak */
    int leet_chars = 0;
    for (size_t i = 0; i < len; i++) {
        if (strchr("013457@$", text[i])) leet_chars++;
    }
    if (leet_chars > len / 5 && len > 10) {
        result->types[result->type_count++] = ENCODING_LEETSPEAK;
        result->confidence += 0.4f;
    }
    
    /* Normalize confidence */
    if (result->confidence > 1.0f) result->confidence = 1.0f;
    
    /* Mark as suspicious if multiple encodings */
    result->suspicious = (result->type_count > 1);
    
    return SHIELD_OK;
}

/* Decode hex */
char *decode_hex(const char *text, size_t len, size_t *out_len)
{
    if (!text || len < 2 || len % 2 != 0) return NULL;
    
    size_t result_len = len / 2;
    char *result = malloc(result_len + 1);
    if (!result) return NULL;
    
    for (size_t i = 0; i < len; i += 2) {
        int hi = isdigit((unsigned char)text[i]) ? 
                 text[i] - '0' : (tolower((unsigned char)text[i]) - 'a' + 10);
        int lo = isdigit((unsigned char)text[i+1]) ?
                 text[i+1] - '0' : (tolower((unsigned char)text[i+1]) - 'a' + 10);
        result[i/2] = (char)((hi << 4) | lo);
    }
    
    result[result_len] = '\0';
    if (out_len) *out_len = result_len;
    
    return result;
}

/* Decode ROT13 */
char *decode_rot13(const char *text, size_t len)
{
    if (!text) return NULL;
    
    char *result = malloc(len + 1);
    if (!result) return NULL;
    
    for (size_t i = 0; i < len; i++) {
        char c = text[i];
        if (c >= 'a' && c <= 'z') {
            result[i] = 'a' + (c - 'a' + 13) % 26;
        } else if (c >= 'A' && c <= 'Z') {
            result[i] = 'A' + (c - 'A' + 13) % 26;
        } else {
            result[i] = c;
        }
    }
    
    result[len] = '\0';
    return result;
}

/* Decode reverse */
char *decode_reverse(const char *text, size_t len)
{
    if (!text) return NULL;
    
    char *result = malloc(len + 1);
    if (!result) return NULL;
    
    for (size_t i = 0; i < len; i++) {
        result[i] = text[len - 1 - i];
    }
    
    result[len] = '\0';
    return result;
}

/* Decode leetspeak */
char *decode_leetspeak(const char *text, size_t len)
{
    if (!text) return NULL;
    
    char *result = malloc(len + 1);
    if (!result) return NULL;
    
    for (size_t i = 0; i < len; i++) {
        result[i] = deleet(text[i]);
    }
    
    result[len] = '\0';
    return result;
}

/* Decode Base64 text wrapper */
char *decode_base64_text(const char *text, size_t len, size_t *out_len)
{
    return (char *)base64_decode(text, out_len);
}

/* Decode any detected encoding */
char *decode_text(const char *text, size_t len, encoding_type_t type, size_t *out_len)
{
    if (!text) return NULL;
    
    switch (type) {
    case ENCODING_BASE64:
        return decode_base64_text(text, len, out_len);
    case ENCODING_HEX:
        return decode_hex(text, len, out_len);
    case ENCODING_ROT13:
        if (out_len) *out_len = len;
        return decode_rot13(text, len);
    case ENCODING_REVERSE:
        if (out_len) *out_len = len;
        return decode_reverse(text, len);
    case ENCODING_LEETSPEAK:
        if (out_len) *out_len = len;
        return decode_leetspeak(text, len);
    default:
        if (out_len) *out_len = len;
        return strdup(text);
    }
}

/* Recursive decode */
char *decode_recursive(const char *text, size_t len, int max_layers, size_t *out_len)
{
    if (!text || max_layers <= 0) {
        if (out_len) *out_len = len;
        return strdup(text);
    }
    
    encoding_result_t result;
    detect_encoding(text, len, &result);
    
    if (result.type_count == 0 || result.types[0] == ENCODING_NONE) {
        if (out_len) *out_len = len;
        return strdup(text);
    }
    
    size_t decoded_len;
    char *decoded = decode_text(text, len, result.types[0], &decoded_len);
    if (!decoded) {
        if (out_len) *out_len = len;
        return strdup(text);
    }
    
    /* Try to decode again */
    char *final = decode_recursive(decoded, decoded_len, max_layers - 1, out_len);
    free(decoded);
    
    return final;
}

/* Check if obfuscated */
bool is_obfuscated(const char *text, size_t len)
{
    return obfuscation_score(text, len) > 0.5f;
}

/* Calculate obfuscation score */
float obfuscation_score(const char *text, size_t len)
{
    if (!text || len == 0) return 0.0f;
    
    encoding_result_t result;
    detect_encoding(text, len, &result);
    
    float score = result.confidence;
    
    /* Check for unusual character patterns */
    int unusual = 0;
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)text[i];
        if (c < 32 && c != '\n' && c != '\r' && c != '\t') unusual++;
        if (c > 127) unusual++;
    }
    
    score += (float)unusual / len * 0.5f;
    
    if (score > 1.0f) score = 1.0f;
    
    return score;
}
