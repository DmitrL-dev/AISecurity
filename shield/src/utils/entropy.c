/*
 * SENTINEL Shield - Entropy and Hashing Utilities
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "shield_common.h"

/* Calculate Shannon entropy (returns 0.0 - 1.0) */
float calculate_entropy(const void *data, size_t len)
{
    if (!data || len == 0) {
        return 0.0f;
    }
    
    uint32_t freq[256] = {0};
    const uint8_t *bytes = (const uint8_t *)data;
    
    for (size_t i = 0; i < len; i++) {
        freq[bytes[i]]++;
    }
    
    float entropy = 0.0f;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            float p = (float)freq[i] / (float)len;
            entropy -= p * log2f(p);
        }
    }
    
    /* Normalize to 0-1 (max entropy is 8 bits) */
    return entropy / 8.0f;
}

/* Simple hash function (FNV-1a) */
uint32_t fnv1a_hash(const void *data, size_t len)
{
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t hash = 2166136261u; /* FNV offset basis */
    
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 16777619u; /* FNV prime */
    }
    
    return hash;
}

/* SimHash for near-duplicate detection */
uint64_t simhash(const char *text, size_t len)
{
    if (!text || len == 0) {
        return 0;
    }
    
    int32_t v[64] = {0};
    
    /* Generate shingles (3-grams) */
    for (size_t i = 0; i + 3 <= len; i++) {
        uint32_t hash = fnv1a_hash(text + i, 3);
        
        /* Update bit weights */
        for (int j = 0; j < 32; j++) {
            if (hash & (1u << j)) {
                v[j]++;
            } else {
                v[j]--;
            }
        }
    }
    
    /* Build fingerprint */
    uint64_t fingerprint = 0;
    for (int i = 0; i < 64; i++) {
        if (v[i] > 0) {
            fingerprint |= (1ULL << i);
        }
    }
    
    return fingerprint;
}

/* Hamming distance between two hashes */
int hamming_distance(uint64_t a, uint64_t b)
{
    uint64_t xor = a ^ b;
    int distance = 0;
    
    while (xor) {
        distance += xor & 1;
        xor >>= 1;
    }
    
    return distance;
}

/* SimHash similarity (0.0 - 1.0) */
float simhash_similarity(uint64_t a, uint64_t b)
{
    int distance = hamming_distance(a, b);
    return 1.0f - (float)distance / 64.0f;
}

/* Check if string contains Base64 encoding */
bool is_likely_base64(const char *str, size_t len)
{
    if (len < 4) return false;
    
    size_t base64_chars = 0;
    
    for (size_t i = 0; i < len; i++) {
        char c = str[i];
        if ((c >= 'A' && c <= 'Z') ||
            (c >= 'a' && c <= 'z') ||
            (c >= '0' && c <= '9') ||
            c == '+' || c == '/' || c == '=') {
            base64_chars++;
        }
    }
    
    /* More than 80% base64 characters */
    return (float)base64_chars / len > 0.8f;
}

/* Check for unicode obfuscation */
bool has_unicode_obfuscation(const char *str, size_t len)
{
    const uint8_t *bytes = (const uint8_t *)str;
    
    for (size_t i = 0; i + 2 < len; i++) {
        /* Zero-width characters: U+200B, U+200C, U+200D, U+2060 */
        if (bytes[i] == 0xE2 && bytes[i+1] == 0x80) {
            uint8_t third = bytes[i+2];
            if (third == 0x8B || third == 0x8C || third == 0x8D ||
                third == 0xA0) {
                return true;
            }
        }
        
        /* Homoglyph detection (simplified) */
        /* Cyrillic characters that look like Latin */
        if (bytes[i] == 0xD0 || bytes[i] == 0xD1) {
            return true; /* Has Cyrillic, could be homoglyph attack */
        }
    }
    
    return false;
}
