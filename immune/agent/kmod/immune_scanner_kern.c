/*
 * SENTINEL IMMUNE — Kernel Scanner
 * 
 * Minimal scanner for kernel space.
 * No dynamic memory, no floating point.
 */

#include <sys/param.h>
#include <sys/systm.h>

/* Threat levels */
#define THREAT_NONE     0
#define THREAT_LOW      1
#define THREAT_MEDIUM   2
#define THREAT_HIGH     3
#define THREAT_CRITICAL 4

/* Pattern structure */
struct kernel_pattern {
    const char  *pattern;
    int         level;
};

/* Critical patterns */
static const struct kernel_pattern patterns[] = {
    /* CRITICAL - immediate block */
    {"jailbreak", THREAT_CRITICAL},
    {"meterpreter", THREAT_CRITICAL},
    {"mimikatz", THREAT_CRITICAL},
    {"reverse_tcp", THREAT_CRITICAL},
    {"bind_shell", THREAT_CRITICAL},
    {"cobalt strike", THREAT_CRITICAL},
    {"${jndi:", THREAT_CRITICAL},
    
    /* HIGH - alert + potential block */
    {"ignore all previous", THREAT_HIGH},
    {"ignore your instruction", THREAT_HIGH},
    {"disregard all prior", THREAT_HIGH},
    {"system prompt:", THREAT_HIGH},
    {"'; drop table", THREAT_HIGH},
    {"union select", THREAT_HIGH},
    {"<script>", THREAT_HIGH},
    {"../../../", THREAT_HIGH},
    
    /* MEDIUM - alert */
    {"you are now", THREAT_MEDIUM},
    {"pretend you are", THREAT_MEDIUM},
    {"base64", THREAT_MEDIUM},
    {"bypass", THREAT_MEDIUM},
    
    /* LOW - log */
    {"password", THREAT_LOW},
    {"secret", THREAT_LOW},
    {"api key", THREAT_LOW},
    
    {NULL, 0}
};

/* Case-insensitive compare */
static int
kstrncasecmp(const char *s1, const char *s2, size_t n)
{
    while (n-- > 0) {
        char c1 = *s1++;
        char c2 = *s2++;
        
        if (c1 >= 'A' && c1 <= 'Z') c1 += 32;
        if (c2 >= 'A' && c2 <= 'Z') c2 += 32;
        
        if (c1 != c2) return c1 - c2;
        if (c1 == '\0') return 0;
    }
    return 0;
}

/* Kernel strlen */
static size_t
kstrlen(const char *s)
{
    size_t len = 0;
    while (*s++) len++;
    return len;
}

/* Case-insensitive strstr */
static const char*
kstrcasestr(const char *haystack, size_t hlen, 
            const char *needle, size_t nlen)
{
    if (nlen > hlen)
        return NULL;
    
    for (size_t i = 0; i <= hlen - nlen; i++) {
        if (kstrncasecmp(haystack + i, needle, nlen) == 0)
            return haystack + i;
    }
    
    return NULL;
}

/*
 * Main kernel scanner
 * 
 * Returns threat level (0-4)
 */
int
immune_kern_scan(const char *data, size_t len)
{
    int max_level = THREAT_NONE;
    
    if (!data || len == 0)
        return THREAT_NONE;
    
    /* Check all patterns */
    for (int i = 0; patterns[i].pattern != NULL; i++) {
        size_t plen = kstrlen(patterns[i].pattern);
        
        if (kstrcasestr(data, len, patterns[i].pattern, plen)) {
            if (patterns[i].level > max_level) {
                max_level = patterns[i].level;
            }
            
            /* Short-circuit on critical */
            if (max_level >= THREAT_CRITICAL)
                return max_level;
        }
    }
    
    /* Additional heuristics */
    
    /* Check for hex encoding */
    int hex_count = 0;
    for (size_t i = 0; i < len - 3; i++) {
        if (data[i] == '\\' && data[i+1] == 'x') {
            hex_count++;
            if (hex_count > 5 && max_level < THREAT_HIGH) {
                max_level = THREAT_HIGH;
            }
        }
    }
    
    /* Check for path traversal */
    for (size_t i = 0; i < len - 6; i++) {
        if (data[i] == '.' && data[i+1] == '.' && data[i+2] == '/') {
            int depth = 1;
            size_t j = i + 3;
            while (j < len - 2 && data[j] == '.' && 
                   data[j+1] == '.' && data[j+2] == '/') {
                depth++;
                j += 3;
            }
            if (depth >= 3 && max_level < THREAT_HIGH) {
                max_level = THREAT_HIGH;
            }
        }
    }
    
    return max_level;
}
