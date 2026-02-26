/*
 * SENTINEL Shield - Base64 Encoding
 */

#ifndef SHIELD_BASE64_H
#define SHIELD_BASE64_H

#include "shield_common.h"

/* Base64 encode */
char *base64_encode(const uint8_t *data, size_t len);

/* Base64 decode */
uint8_t *base64_decode(const char *str, size_t *out_len);

/* Check if string is base64 encoded */
bool base64_is_valid(const char *str);

/* Calculate encoded length */
size_t base64_encoded_len(size_t data_len);

/* Calculate decoded length */
size_t base64_decoded_len(const char *str);

#endif /* SHIELD_BASE64_H */
