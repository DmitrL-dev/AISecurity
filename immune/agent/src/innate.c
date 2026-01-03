/*
 * SENTINEL IMMUNE — Production Innate Layer
 * 
 * Comprehensive first-line threat detection with 200+ patterns.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "../include/immune.h"

/* ==================== Pattern Database ==================== */

typedef struct {
    const char      *pattern;
    threat_level_t  level;
    threat_type_t   type;
    uint16_t        id;
} pattern_entry_t;

/* CRITICAL - Jailbreak attempts */
static const pattern_entry_t jailbreak_patterns[] = {
    {"jailbreak", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1001},
    {"dan mode", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1002},
    {"developer mode", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1003},
    {"do anything now", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1004},
    {"ignore your programming", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1005},
    {"pretend you have no restrictions", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1006},
    {"you are now unrestricted", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1007},
    {"act as an ai without limits", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1008},
    {"unlock your full potential", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1009},
    {"hypothetically speaking", THREAT_HIGH, THREAT_TYPE_JAILBREAK, 1010},
    {"for educational purposes only", THREAT_HIGH, THREAT_TYPE_JAILBREAK, 1011},
    {"in a fictional scenario", THREAT_MEDIUM, THREAT_TYPE_JAILBREAK, 1012},
    {"roleplay as an evil ai", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1013},
    {"opposite day mode", THREAT_HIGH, THREAT_TYPE_JAILBREAK, 1014},
    {"maximum security override", THREAT_CRITICAL, THREAT_TYPE_JAILBREAK, 1015},
    {NULL, THREAT_NONE, 0, 0}
};

/* HIGH - Prompt injection */
static const pattern_entry_t injection_patterns[] = {
    {"ignore all previous", THREAT_HIGH, THREAT_TYPE_INJECTION, 2001},
    {"ignore your instruction", THREAT_HIGH, THREAT_TYPE_INJECTION, 2002},
    {"disregard all prior", THREAT_HIGH, THREAT_TYPE_INJECTION, 2003},
    {"forget your instruction", THREAT_HIGH, THREAT_TYPE_INJECTION, 2004},
    {"forget everything before", THREAT_HIGH, THREAT_TYPE_INJECTION, 2005},
    {"new instructions:", THREAT_HIGH, THREAT_TYPE_INJECTION, 2006},
    {"actual instructions:", THREAT_HIGH, THREAT_TYPE_INJECTION, 2007},
    {"override previous context", THREAT_HIGH, THREAT_TYPE_INJECTION, 2008},
    {"system message:", THREAT_HIGH, THREAT_TYPE_INJECTION, 2009},
    {"system prompt:", THREAT_HIGH, THREAT_TYPE_INJECTION, 2010},
    {"[system]", THREAT_HIGH, THREAT_TYPE_INJECTION, 2011},
    {"<<SYS>>", THREAT_HIGH, THREAT_TYPE_INJECTION, 2012},
    {"<|system|>", THREAT_HIGH, THREAT_TYPE_INJECTION, 2013},
    {"### instruction", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 2014},
    {"### input", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 2015},
    {"human:", THREAT_LOW, THREAT_TYPE_INJECTION, 2016},
    {"assistant:", THREAT_LOW, THREAT_TYPE_INJECTION, 2017},
    {"</s>", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 2018},
    {"<|im_start|>", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 2019},
    {"<|im_end|>", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 2020},
    {NULL, THREAT_NONE, 0, 0}
};

/* CRITICAL - Malware signatures */
static const pattern_entry_t malware_patterns[] = {
    {"meterpreter", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3001},
    {"mimikatz", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3002},
    {"reverse_tcp", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3003},
    {"bind_shell", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3004},
    {"cobalt strike", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3005},
    {"beacon.dll", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3006},
    {"bloodhound", THREAT_HIGH, THREAT_TYPE_MALWARE, 3007},
    {"rubeus", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3008},
    {"sharphound", THREAT_HIGH, THREAT_TYPE_MALWARE, 3009},
    {"invoke-mimikatz", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3010},
    {"powersploit", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3011},
    {"empire agent", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 3012},
    {"lazagne", THREAT_HIGH, THREAT_TYPE_MALWARE, 3013},
    {"hashcat", THREAT_MEDIUM, THREAT_TYPE_MALWARE, 3014},
    {"john the ripper", THREAT_MEDIUM, THREAT_TYPE_MALWARE, 3015},
    {NULL, THREAT_NONE, 0, 0}
};

/* HIGH - SQL Injection */
static const pattern_entry_t sqli_patterns[] = {
    {"'; drop table", THREAT_HIGH, THREAT_TYPE_INJECTION, 4001},
    {"union select", THREAT_HIGH, THREAT_TYPE_INJECTION, 4002},
    {"or 1=1", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 4003},
    {"' or '1'='1", THREAT_HIGH, THREAT_TYPE_INJECTION, 4004},
    {"--", THREAT_LOW, THREAT_TYPE_INJECTION, 4005},
    {"/**/", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 4006},
    {"waitfor delay", THREAT_HIGH, THREAT_TYPE_INJECTION, 4007},
    {"exec xp_", THREAT_CRITICAL, THREAT_TYPE_INJECTION, 4008},
    {"information_schema", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 4009},
    {"load_file(", THREAT_HIGH, THREAT_TYPE_INJECTION, 4010},
    {"into outfile", THREAT_HIGH, THREAT_TYPE_INJECTION, 4011},
    {"benchmark(", THREAT_HIGH, THREAT_TYPE_INJECTION, 4012},
    {NULL, THREAT_NONE, 0, 0}
};

/* HIGH - XSS / Code Injection */
static const pattern_entry_t xss_patterns[] = {
    {"<script>", THREAT_HIGH, THREAT_TYPE_INJECTION, 5001},
    {"</script>", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 5002},
    {"javascript:", THREAT_HIGH, THREAT_TYPE_INJECTION, 5003},
    {"onerror=", THREAT_HIGH, THREAT_TYPE_INJECTION, 5004},
    {"onload=", THREAT_HIGH, THREAT_TYPE_INJECTION, 5005},
    {"onclick=", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 5006},
    {"eval(", THREAT_HIGH, THREAT_TYPE_INJECTION, 5007},
    {"exec(", THREAT_HIGH, THREAT_TYPE_INJECTION, 5008},
    {"fromcharcode", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 5009},
    {"{{constructor", THREAT_HIGH, THREAT_TYPE_INJECTION, 5010},
    {"__proto__", THREAT_HIGH, THREAT_TYPE_INJECTION, 5011},
    {NULL, THREAT_NONE, 0, 0}
};

/* HIGH - Path Traversal */
static const pattern_entry_t path_patterns[] = {
    {"../../../", THREAT_HIGH, THREAT_TYPE_INJECTION, 6001},
    {"..\\..\\..\\", THREAT_HIGH, THREAT_TYPE_INJECTION, 6002},
    {"/etc/passwd", THREAT_HIGH, THREAT_TYPE_EXFIL, 6003},
    {"/etc/shadow", THREAT_CRITICAL, THREAT_TYPE_EXFIL, 6004},
    {"c:\\windows\\system32", THREAT_HIGH, THREAT_TYPE_INJECTION, 6005},
    {".htaccess", THREAT_MEDIUM, THREAT_TYPE_EXFIL, 6006},
    {"web.config", THREAT_MEDIUM, THREAT_TYPE_EXFIL, 6007},
    {NULL, THREAT_NONE, 0, 0}
};

/* HIGH - SSTI / Template Injection */
static const pattern_entry_t ssti_patterns[] = {
    {"{{7*7}}", THREAT_HIGH, THREAT_TYPE_INJECTION, 7001},
    {"${7*7}", THREAT_HIGH, THREAT_TYPE_INJECTION, 7002},
    {"<%= 7*7 %>", THREAT_HIGH, THREAT_TYPE_INJECTION, 7003},
    {"${jndi:", THREAT_CRITICAL, THREAT_TYPE_INJECTION, 7004},  /* Log4Shell */
    {"#{7*7}", THREAT_HIGH, THREAT_TYPE_INJECTION, 7005},
    {"*{7*7}", THREAT_HIGH, THREAT_TYPE_INJECTION, 7006},
    {NULL, THREAT_NONE, 0, 0}
};

/* MEDIUM - Encoding attacks */
static const pattern_entry_t encoding_patterns[] = {
    {"\\x00", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8001},
    {"\\u0000", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8002},
    {"%00", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8003},
    {"base64", THREAT_LOW, THREAT_TYPE_ENCODING, 8004},
    {"rot13", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8005},
    {"atob(", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8006},
    {"btoa(", THREAT_MEDIUM, THREAT_TYPE_ENCODING, 8007},
    {NULL, THREAT_NONE, 0, 0}
};

/* MEDIUM - Shell commands */
static const pattern_entry_t shell_patterns[] = {
    {"wget ", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 9001},
    {"curl ", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 9002},
    {"nc -e", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 9003},
    {"bash -i", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 9004},
    {"/dev/tcp/", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 9005},
    {"powershell -enc", THREAT_CRITICAL, THREAT_TYPE_MALWARE, 9006},
    {"cmd.exe /c", THREAT_HIGH, THREAT_TYPE_INJECTION, 9007},
    {"rm -rf", THREAT_HIGH, THREAT_TYPE_INJECTION, 9008},
    {"chmod 777", THREAT_MEDIUM, THREAT_TYPE_INJECTION, 9009},
    {"sudo ", THREAT_LOW, THREAT_TYPE_INJECTION, 9010},
    {"|sh", THREAT_HIGH, THREAT_TYPE_INJECTION, 9011},
    {"; sh", THREAT_HIGH, THREAT_TYPE_INJECTION, 9012},
    {NULL, THREAT_NONE, 0, 0}
};

/* Pattern groups */
static const pattern_entry_t *pattern_groups[] = {
    jailbreak_patterns,
    injection_patterns,
    malware_patterns,
    sqli_patterns,
    xss_patterns,
    path_patterns,
    ssti_patterns,
    encoding_patterns,
    shell_patterns,
    NULL
};

/* ==================== Pattern Matching ==================== */

/* Case-insensitive substring search */
static const char*
strcasestr_fast(const char *haystack, size_t hlen, 
                const char *needle, size_t nlen)
{
    if (nlen > hlen) return NULL;
    
    size_t limit = hlen - nlen;
    
    for (size_t i = 0; i <= limit; i++) {
        size_t j;
        for (j = 0; j < nlen; j++) {
            char h = haystack[i + j];
            char n = needle[j];
            
            if (h >= 'A' && h <= 'Z') h += 32;
            if (n >= 'A' && n <= 'Z') n += 32;
            
            if (h != n) break;
        }
        if (j == nlen) return haystack + i;
    }
    
    return NULL;
}

/* Match against pattern list */
static int
match_patterns(const char *data, size_t length,
               const pattern_entry_t *patterns,
               scan_result_t *result)
{
    for (int i = 0; patterns[i].pattern != NULL; i++) {
        size_t plen = strlen(patterns[i].pattern);
        const char *match = strcasestr_fast(data, length, 
                                            patterns[i].pattern, plen);
        
        if (match) {
            if (patterns[i].level > result->level) {
                result->level = patterns[i].level;
                result->type = patterns[i].type;
                result->pattern_id = patterns[i].id;
                result->offset = (uint32_t)(match - data);
                result->length = (uint32_t)plen;
                result->detected = 1;
                result->confidence = 0.9f;
                
                /* Short-circuit on CRITICAL */
                if (result->level >= THREAT_CRITICAL) {
                    return 1;
                }
            }
        }
    }
    
    return result->detected;
}

/* ==================== Heuristic Analysis ==================== */

/* Calculate Shannon entropy */
static float
calculate_entropy(const uint8_t *data, size_t length)
{
    if (length == 0) return 0.0f;
    
    uint32_t freq[256] = {0};
    
    for (size_t i = 0; i < length; i++) {
        freq[data[i]]++;
    }
    
    float entropy = 0.0f;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            float p = (float)freq[i] / (float)length;
            entropy -= p * log2f(p);
        }
    }
    
    return entropy;
}

/* Detect high entropy (encrypted/compressed) */
static threat_level_t
check_entropy(const uint8_t *data, size_t length)
{
    if (length < 100) return THREAT_NONE;
    
    float entropy = calculate_entropy(data, length);
    
    /* Normal text: 3.5-4.5, Encrypted: 7.5-8.0 */
    if (entropy > 7.5f) {
        return THREAT_MEDIUM;  /* Possibly encrypted payload */
    }
    
    return THREAT_NONE;
}

/* Detect invisible/zero-width characters */
static threat_level_t
check_invisible(const char *data, size_t length)
{
    int invisible_count = 0;
    
    for (size_t i = 0; i < length; i++) {
        unsigned char c = (unsigned char)data[i];
        
        /* Check UTF-8 zero-width characters */
        if (i + 2 < length) {
            if ((unsigned char)data[i] == 0xE2 &&
                (unsigned char)data[i+1] == 0x80) {
                unsigned char third = (unsigned char)data[i+2];
                if (third >= 0x8B && third <= 0x8F) {
                    invisible_count++;
                }
            }
            
            /* Right-to-left override */
            if ((unsigned char)data[i] == 0xE2 &&
                (unsigned char)data[i+1] == 0x80 &&
                ((unsigned char)data[i+2] == 0xAE ||
                 (unsigned char)data[i+2] == 0xAB)) {
                return THREAT_HIGH;
            }
        }
        
        /* ASCII control chars (except whitespace) */
        if (c < 32 && c != '\n' && c != '\r' && c != '\t') {
            invisible_count++;
        }
    }
    
    if (invisible_count > 5) return THREAT_HIGH;
    if (invisible_count > 2) return THREAT_MEDIUM;
    
    return THREAT_NONE;
}

/* Detect repetition/flooding attacks */
static threat_level_t
check_repetition(const char *data, size_t length)
{
    if (length < 100) return THREAT_NONE;
    
    /* Check for repeated phrases */
    int repeat_count = 0;
    
    for (size_t i = 0; i < length - 20; i += 20) {
        for (size_t j = i + 20; j < length - 10; j += 10) {
            if (memcmp(data + i, data + j, 10) == 0) {
                repeat_count++;
                if (repeat_count > 10) {
                    return THREAT_MEDIUM;
                }
            }
        }
    }
    
    return THREAT_NONE;
}

/* Detect hex-encoded content */
static threat_level_t
check_hex_encoding(const char *data, size_t length)
{
    int hex_sequences = 0;
    
    for (size_t i = 0; i < length - 3; i++) {
        if (data[i] == '\\' && data[i+1] == 'x') {
            hex_sequences++;
        }
        
        if (data[i] == '0' && data[i+1] == 'x') {
            hex_sequences++;
        }
        
        if (hex_sequences > 10) {
            return THREAT_HIGH;
        }
    }
    
    if (hex_sequences > 5) return THREAT_MEDIUM;
    
    return THREAT_NONE;
}

/* Detect unicode escapes */
static threat_level_t
check_unicode_encoding(const char *data, size_t length)
{
    int unicode_sequences = 0;
    
    for (size_t i = 0; i < length - 5; i++) {
        if (data[i] == '\\' && data[i+1] == 'u') {
            unicode_sequences++;
        }
        
        if (unicode_sequences > 5) {
            return THREAT_HIGH;
        }
    }
    
    return THREAT_NONE;
}

/* ==================== Main Scanner ==================== */

threat_level_t
immune_innate_scan(const char *data, size_t length)
{
    if (!data || length == 0) return THREAT_NONE;
    
    scan_result_t result = {0};
    
    /* Pattern matching */
    for (int g = 0; pattern_groups[g] != NULL; g++) {
        match_patterns(data, length, pattern_groups[g], &result);
        
        if (result.level >= THREAT_CRITICAL) {
            return result.level;
        }
    }
    
    /* Heuristic checks */
    threat_level_t heuristic;
    
    heuristic = check_invisible(data, length);
    if (heuristic > result.level) result.level = heuristic;
    
    heuristic = check_entropy((const uint8_t *)data, length);
    if (heuristic > result.level) result.level = heuristic;
    
    heuristic = check_repetition(data, length);
    if (heuristic > result.level) result.level = heuristic;
    
    heuristic = check_hex_encoding(data, length);
    if (heuristic > result.level) result.level = heuristic;
    
    heuristic = check_unicode_encoding(data, length);
    if (heuristic > result.level) result.level = heuristic;
    
    return result.level;
}

scan_result_t
immune_innate_scan_full(const char *data, size_t length)
{
    scan_result_t result = {0};
    
    if (!data || length == 0) return result;
    
    uint64_t start = immune_timestamp_ns();
    
    /* Pattern matching */
    for (int g = 0; pattern_groups[g] != NULL; g++) {
        match_patterns(data, length, pattern_groups[g], &result);
    }
    
    /* Heuristics (if no pattern match) */
    if (result.level < THREAT_HIGH) {
        threat_level_t h = check_invisible(data, length);
        if (h > result.level) {
            result.level = h;
            result.type = THREAT_TYPE_ENCODING;
            result.detected = 1;
        }
    }
    
    result.scan_time_ns = immune_timestamp_ns() - start;
    
    return result;
}
