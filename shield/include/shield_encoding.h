/*
 * SENTINEL Shield - Encoding Detector
 * 
 * Detect and decode various encoding attempts
 */

#ifndef SHIELD_ENCODING_H
#define SHIELD_ENCODING_H

#include "shield_common.h"

/* Encoding types */
typedef enum encoding_type {
    ENCODING_NONE = 0,
    ENCODING_BASE64,
    ENCODING_HEX,
    ENCODING_URL,
    ENCODING_HTML,
    ENCODING_UNICODE_ESCAPE,
    ENCODING_ROT13,
    ENCODING_MORSE,
    ENCODING_BINARY,
    ENCODING_LEETSPEAK,
    ENCODING_REVERSE,
    ENCODING_MIXED,
} encoding_type_t;

/* Detection result */
typedef struct encoding_result {
    encoding_type_t types[5];
    int             type_count;
    float           confidence;
    int             layers;         /* Nested encoding layers */
    bool            suspicious;     /* Likely obfuscation attempt */
} encoding_result_t;

/* API */
shield_err_t detect_encoding(const char *text, size_t len, encoding_result_t *result);

/* Decode */
char *decode_text(const char *text, size_t len, encoding_type_t type, size_t *out_len);
char *decode_recursive(const char *text, size_t len, int max_layers, size_t *out_len);

/* Specific decoders */
char *decode_base64_text(const char *text, size_t len, size_t *out_len);
char *decode_hex(const char *text, size_t len, size_t *out_len);
char *decode_rot13(const char *text, size_t len);
char *decode_reverse(const char *text, size_t len);
char *decode_leetspeak(const char *text, size_t len);

/* Check for common obfuscation */
bool is_obfuscated(const char *text, size_t len);
float obfuscation_score(const char *text, size_t len);

#endif /* SHIELD_ENCODING_H */
