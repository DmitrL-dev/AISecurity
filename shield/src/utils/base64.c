/*
 * SENTINEL Shield - Base64 Encoding Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_base64.h"

static const char b64_table[] = 
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static const uint8_t b64_decode_table[256] = {
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 62, 64, 64, 64, 63,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 64, 64, 64, 64, 64, 64,
    64,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 64, 64, 64, 64, 64,
    64, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64
};

/* Calculate encoded length */
size_t base64_encoded_len(size_t data_len)
{
    return ((data_len + 2) / 3) * 4;
}

/* Encode */
char *base64_encode(const uint8_t *data, size_t len)
{
    if (!data) return NULL;
    
    size_t out_len = base64_encoded_len(len);
    char *out = malloc(out_len + 1);
    if (!out) return NULL;
    
    size_t i, j;
    for (i = 0, j = 0; i < len; ) {
        uint32_t a = i < len ? data[i++] : 0;
        uint32_t b = i < len ? data[i++] : 0;
        uint32_t c = i < len ? data[i++] : 0;
        
        uint32_t triple = (a << 16) | (b << 8) | c;
        
        out[j++] = b64_table[(triple >> 18) & 0x3F];
        out[j++] = b64_table[(triple >> 12) & 0x3F];
        out[j++] = b64_table[(triple >> 6) & 0x3F];
        out[j++] = b64_table[triple & 0x3F];
    }
    
    /* Padding */
    if (len % 3 >= 1) out[out_len - 1] = '=';
    if (len % 3 == 1) out[out_len - 2] = '=';
    
    out[out_len] = '\0';
    return out;
}

/* Calculate decoded length */
size_t base64_decoded_len(const char *str)
{
    if (!str) return 0;
    
    size_t len = strlen(str);
    if (len == 0) return 0;
    
    size_t padding = 0;
    if (str[len - 1] == '=') padding++;
    if (len > 1 && str[len - 2] == '=') padding++;
    
    return (len / 4) * 3 - padding;
}

/* Decode */
uint8_t *base64_decode(const char *str, size_t *out_len)
{
    if (!str || !out_len) return NULL;
    
    size_t len = strlen(str);
    if (len % 4 != 0) return NULL;
    
    *out_len = base64_decoded_len(str);
    
    uint8_t *out = malloc(*out_len + 1);
    if (!out) return NULL;
    
    size_t i, j;
    for (i = 0, j = 0; i < len; ) {
        uint8_t a = b64_decode_table[(uint8_t)str[i++]];
        uint8_t b = b64_decode_table[(uint8_t)str[i++]];
        uint8_t c = b64_decode_table[(uint8_t)str[i++]];
        uint8_t d = b64_decode_table[(uint8_t)str[i++]];
        
        if (a == 64 || b == 64) {
            free(out);
            return NULL;
        }
        
        uint32_t triple = (a << 18) | (b << 12) | ((c & 63) << 6) | (d & 63);
        
        if (j < *out_len) out[j++] = (triple >> 16) & 0xFF;
        if (j < *out_len) out[j++] = (triple >> 8) & 0xFF;
        if (j < *out_len) out[j++] = triple & 0xFF;
    }
    
    out[*out_len] = '\0';
    return out;
}

/* Check if valid base64 */
bool base64_is_valid(const char *str)
{
    if (!str) return false;
    
    size_t len = strlen(str);
    if (len % 4 != 0) return false;
    if (len == 0) return true;
    
    size_t padding = 0;
    for (size_t i = 0; i < len; i++) {
        char c = str[i];
        if (c == '=') {
            padding++;
            if (padding > 2) return false;
            if (i < len - 2) return false;
        } else if (b64_decode_table[(uint8_t)c] == 64) {
            return false;
        }
    }
    
    return true;
}
