/*
 * SENTINEL IMMUNE — Kill Switch Implementation
 * 
 * Shamir's Secret Sharing over GF(256) for decentralized shutdown.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

#ifdef __unix__
#include <unistd.h>
#include <fcntl.h>
#endif

#include "kill_switch.h"

/* ==================== GF(256) Arithmetic ==================== */

/* 
 * GF(256) operations using AES irreducible polynomial: x^8 + x^4 + x^3 + x + 1
 * This is the standard Rijndael polynomial.
 */

/* Logarithm table for GF(256) */
static const uint8_t gf256_log[256] = {
    0x00, 0x00, 0x19, 0x01, 0x32, 0x02, 0x1a, 0xc6,
    0x4b, 0xc7, 0x1b, 0x68, 0x33, 0xee, 0xdf, 0x03,
    0x64, 0x04, 0xe0, 0x0e, 0x34, 0x8d, 0x81, 0xef,
    0x4c, 0x71, 0x08, 0xc8, 0xf8, 0x69, 0x1c, 0xc1,
    0x7d, 0xc2, 0x1d, 0xb5, 0xf9, 0xb9, 0x27, 0x6a,
    0x4d, 0xe4, 0xa6, 0x72, 0x9a, 0xc9, 0x09, 0x78,
    0x65, 0x2f, 0x8a, 0x05, 0x21, 0x0f, 0xe1, 0x24,
    0x12, 0xf0, 0x82, 0x45, 0x35, 0x93, 0xda, 0x8e,
    0x96, 0x8f, 0xdb, 0xbd, 0x36, 0xd0, 0xce, 0x94,
    0x13, 0x5c, 0xd2, 0xf1, 0x40, 0x46, 0x83, 0x38,
    0x66, 0xdd, 0xfd, 0x30, 0xbf, 0x06, 0x8b, 0x62,
    0xb3, 0x25, 0xe2, 0x98, 0x22, 0x88, 0x91, 0x10,
    0x7e, 0x6e, 0x48, 0xc3, 0xa3, 0xb6, 0x1e, 0x42,
    0x3a, 0x6b, 0x28, 0x54, 0xfa, 0x85, 0x3d, 0xba,
    0x2b, 0x79, 0x0a, 0x15, 0x9b, 0x9f, 0x5e, 0xca,
    0x4e, 0xd4, 0xac, 0xe5, 0xf3, 0x73, 0xa7, 0x57,
    0xaf, 0x58, 0xa8, 0x50, 0xf4, 0xea, 0xd6, 0x74,
    0x4f, 0xae, 0xe9, 0xd5, 0xe7, 0xe6, 0xad, 0xe8,
    0x2c, 0xd7, 0x75, 0x7a, 0xeb, 0x16, 0x0b, 0xf5,
    0x59, 0xcb, 0x5f, 0xb0, 0x9c, 0xa9, 0x51, 0xa0,
    0x7f, 0x0c, 0xf6, 0x6f, 0x17, 0xc4, 0x49, 0xec,
    0xd8, 0x43, 0x1f, 0x2d, 0xa4, 0x76, 0x7b, 0xb7,
    0xcc, 0xbb, 0x3e, 0x5a, 0xfb, 0x60, 0xb1, 0x86,
    0x3b, 0x52, 0xa1, 0x6c, 0xaa, 0x55, 0x29, 0x9d,
    0x97, 0xb2, 0x87, 0x90, 0x61, 0xbe, 0xdc, 0xfc,
    0xbc, 0x95, 0xcf, 0xcd, 0x37, 0x3f, 0x5b, 0xd1,
    0x53, 0x39, 0x84, 0x3c, 0x41, 0xa2, 0x6d, 0x47,
    0x14, 0x2a, 0x9e, 0x5d, 0x56, 0xf2, 0xd3, 0xab,
    0x44, 0x11, 0x92, 0xd9, 0x23, 0x20, 0x2e, 0x89,
    0xb4, 0x7c, 0xb8, 0x26, 0x77, 0x99, 0xe3, 0xa5,
    0x67, 0x4a, 0xed, 0xde, 0xc5, 0x31, 0xfe, 0x18,
    0x0d, 0x63, 0x8c, 0x80, 0xc0, 0xf7, 0x70, 0x07
};

/* Exponent table for GF(256) */
static const uint8_t gf256_exp[256] = {
    0x01, 0x03, 0x05, 0x0f, 0x11, 0x33, 0x55, 0xff,
    0x1a, 0x2e, 0x72, 0x96, 0xa1, 0xf8, 0x13, 0x35,
    0x5f, 0xe1, 0x38, 0x48, 0xd8, 0x73, 0x95, 0xa4,
    0xf7, 0x02, 0x06, 0x0a, 0x1e, 0x22, 0x66, 0xaa,
    0xe5, 0x34, 0x5c, 0xe4, 0x37, 0x59, 0xeb, 0x26,
    0x6a, 0xbe, 0xd9, 0x70, 0x90, 0xab, 0xe6, 0x31,
    0x53, 0xf5, 0x04, 0x0c, 0x14, 0x3c, 0x44, 0xcc,
    0x4f, 0xd1, 0x68, 0xb8, 0xd3, 0x6e, 0xb2, 0xcd,
    0x4c, 0xd4, 0x67, 0xa9, 0xe0, 0x3b, 0x4d, 0xd7,
    0x62, 0xa6, 0xf1, 0x08, 0x18, 0x28, 0x78, 0x88,
    0x83, 0x9e, 0xb9, 0xd0, 0x6b, 0xbd, 0xdc, 0x7f,
    0x81, 0x98, 0xb3, 0xce, 0x49, 0xdb, 0x76, 0x9a,
    0xb5, 0xc4, 0x57, 0xf9, 0x10, 0x30, 0x50, 0xf0,
    0x0b, 0x1d, 0x27, 0x69, 0xbb, 0xd6, 0x61, 0xa3,
    0xfe, 0x19, 0x2b, 0x7d, 0x87, 0x92, 0xad, 0xec,
    0x2f, 0x71, 0x93, 0xae, 0xe9, 0x20, 0x60, 0xa0,
    0xfb, 0x16, 0x3a, 0x4e, 0xd2, 0x6d, 0xb7, 0xc2,
    0x5d, 0xe7, 0x32, 0x56, 0xfa, 0x15, 0x3f, 0x41,
    0xc3, 0x5e, 0xe2, 0x3d, 0x47, 0xc9, 0x40, 0xc0,
    0x5b, 0xed, 0x2c, 0x74, 0x9c, 0xbf, 0xda, 0x75,
    0x9f, 0xba, 0xd5, 0x64, 0xac, 0xef, 0x2a, 0x7e,
    0x82, 0x9d, 0xbc, 0xdf, 0x7a, 0x8e, 0x89, 0x80,
    0x9b, 0xb6, 0xc1, 0x58, 0xe8, 0x23, 0x65, 0xaf,
    0xea, 0x25, 0x6f, 0xb1, 0xc8, 0x43, 0xc5, 0x54,
    0xfc, 0x1f, 0x21, 0x63, 0xa5, 0xf4, 0x07, 0x09,
    0x1b, 0x2d, 0x77, 0x99, 0xb0, 0xcb, 0x46, 0xca,
    0x45, 0xcf, 0x4a, 0xde, 0x79, 0x8b, 0x86, 0x91,
    0xa8, 0xe3, 0x3e, 0x42, 0xc6, 0x51, 0xf3, 0x0e,
    0x12, 0x36, 0x5a, 0xee, 0x29, 0x7b, 0x8d, 0x8c,
    0x8f, 0x8a, 0x85, 0x94, 0xa7, 0xf2, 0x0d, 0x17,
    0x39, 0x4b, 0xdd, 0x7c, 0x84, 0x97, 0xa2, 0xfd,
    0x1c, 0x24, 0x6c, 0xb4, 0xc7, 0x52, 0xf6, 0x01
};

/* GF(256) multiplication */
static inline uint8_t
gf256_mul(uint8_t a, uint8_t b)
{
    if (a == 0 || b == 0) return 0;
    return gf256_exp[(gf256_log[a] + gf256_log[b]) % 255];
}

/* GF(256) division */
static inline uint8_t
gf256_div(uint8_t a, uint8_t b)
{
    if (b == 0) return 0;  /* Division by zero */
    if (a == 0) return 0;
    int log_diff = gf256_log[a] - gf256_log[b];
    if (log_diff < 0) log_diff += 255;
    return gf256_exp[log_diff];
}

/* ==================== Secure Random ==================== */

static int
secure_random(uint8_t *buf, size_t len)
{
#ifdef __unix__
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, buf, len);
    close(fd);
    return (n == (ssize_t)len) ? 0 : -1;
#else
    /* Fallback to time-seeded rand() - NOT SECURE */
    static int seeded = 0;
    if (!seeded) {
        srand((unsigned int)time(NULL));
        seeded = 1;
    }
    for (size_t i = 0; i < len; i++) {
        buf[i] = (uint8_t)(rand() & 0xFF);
    }
    return 0;
#endif
}

/* ==================== Global State ==================== */

static struct {
    bool            initialized;
    kill_config_t   config;
    kill_state_t    state;
    
    /* Collected shares for activation */
    kill_share_t    shares[KILL_MAX_SHARES];
    int             share_count;
    pthread_mutex_t share_lock;
    
    /* Canary */
    time_t          canary_last_publish;
    time_t          canary_last_seen;
} g_kill = {0};

static const char* state_strings[] = {
    [KILL_STATE_NORMAL]    = "Normal",
    [KILL_STATE_ARMED]     = "Armed",
    [KILL_STATE_TRIGGERED] = "Triggered",
    [KILL_STATE_SAFE_MODE] = "Safe Mode"
};

const char*
kill_state_string(kill_state_t state)
{
    if (state >= 0 && state <= KILL_STATE_SAFE_MODE) {
        return state_strings[state];
    }
    return "Unknown";
}

void
kill_secure_zero(void *ptr, size_t size)
{
    volatile uint8_t *p = (volatile uint8_t *)ptr;
    while (size--) {
        *p++ = 0;
    }
}

/* ==================== Configuration ==================== */

void
kill_config_init(kill_config_t *config)
{
    if (!config) return;
    
    config->threshold = KILL_DEFAULT_THRESHOLD;
    config->total_shares = KILL_DEFAULT_SHARES;
    config->canary_hours = KILL_CANARY_HOURS;
    config->canary_expire = KILL_CANARY_EXPIRE_HOURS;
    strncpy(config->canary_url, "/canary", 255);
}

/* ==================== Shamir Secret Sharing ==================== */

int
kill_generate_secret(uint8_t *secret)
{
    if (!secret) return -1;
    return secure_random(secret, KILL_SECRET_SIZE);
}

int
kill_generate_shares(const uint8_t *secret,
                     kill_share_t *shares,
                     int n,
                     int m)
{
    if (!secret || !shares || n < 2 || m < 2 || m > n || n > KILL_MAX_SHARES) {
        return -1;
    }
    
    /* Generate random coefficients for polynomial */
    uint8_t coeffs[KILL_SECRET_SIZE][KILL_MAX_SHARES];
    
    for (int byte = 0; byte < KILL_SECRET_SIZE; byte++) {
        coeffs[byte][0] = secret[byte];  /* a0 = secret */
        for (int i = 1; i < m; i++) {
            secure_random(&coeffs[byte][i], 1);
        }
    }
    
    /* Evaluate polynomial at x = 1, 2, ..., n */
    for (int i = 0; i < n; i++) {
        shares[i].id = i + 1;  /* x = 1, 2, ..., n */
        shares[i].valid = true;
        shares[i].created = time(NULL);
        snprintf(shares[i].name, sizeof(shares[i].name), "Share %d", i + 1);
        
        uint8_t x = shares[i].id;
        
        for (int byte = 0; byte < KILL_SECRET_SIZE; byte++) {
            /* f(x) = a0 + a1*x + a2*x^2 + ... */
            uint8_t y = 0;
            uint8_t x_pow = 1;
            
            for (int j = 0; j < m; j++) {
                y ^= gf256_mul(coeffs[byte][j], x_pow);
                x_pow = gf256_mul(x_pow, x);
            }
            
            shares[i].share[byte + 1] = y;  /* +1 for ID */
        }
        shares[i].share[0] = x;  /* Store x in first byte */
    }
    
    /* Zero coefficients */
    kill_secure_zero(coeffs, sizeof(coeffs));
    
    return 0;
}

int
kill_combine_shares(const kill_share_t *shares,
                    int m,
                    uint8_t *secret)
{
    if (!shares || !secret || m < 2) {
        return -1;
    }
    
    /* Lagrange interpolation at x = 0 */
    for (int byte = 0; byte < KILL_SECRET_SIZE; byte++) {
        uint8_t sum = 0;
        
        for (int i = 0; i < m; i++) {
            uint8_t xi = shares[i].share[0];  /* x value from share */
            uint8_t yi = shares[i].share[byte + 1];
            
            /* Calculate Lagrange basis polynomial L_i(0) */
            uint8_t num = 1;
            uint8_t den = 1;
            
            for (int j = 0; j < m; j++) {
                if (i == j) continue;
                
                uint8_t xj = shares[j].share[0];
                
                /* num *= (0 - xj) = xj */
                num = gf256_mul(num, xj);
                
                /* den *= (xi - xj) */
                den = gf256_mul(den, xi ^ xj);
            }
            
            /* L_i(0) * y_i */
            uint8_t term = gf256_mul(yi, gf256_div(num, den));
            sum ^= term;
        }
        
        secret[byte] = sum;
    }
    
    return 0;
}

/* ==================== Kill Switch Control ==================== */

int
kill_init(const kill_config_t *config)
{
    if (g_kill.initialized) return 0;
    
    memset(&g_kill, 0, sizeof(g_kill));
    
    if (config) {
        memcpy(&g_kill.config, config, sizeof(kill_config_t));
    } else {
        kill_config_init(&g_kill.config);
    }
    
    pthread_mutex_init(&g_kill.share_lock, NULL);
    g_kill.state = KILL_STATE_NORMAL;
    g_kill.initialized = true;
    
    printf("[KILL] Initialized: %d-of-%d threshold\n",
           g_kill.config.threshold, g_kill.config.total_shares);
    
    return 0;
}

kill_state_t
kill_get_state(void)
{
    return g_kill.state;
}

int
kill_submit_share(const kill_share_t *share)
{
    if (!g_kill.initialized || !share || !share->valid) {
        return -1;
    }
    
    pthread_mutex_lock(&g_kill.share_lock);
    
    /* Check if already have this share */
    for (int i = 0; i < g_kill.share_count; i++) {
        if (g_kill.shares[i].id == share->id) {
            pthread_mutex_unlock(&g_kill.share_lock);
            return g_kill.share_count;  /* Already have it */
        }
    }
    
    /* Add share */
    if (g_kill.share_count < KILL_MAX_SHARES) {
        memcpy(&g_kill.shares[g_kill.share_count], share, sizeof(kill_share_t));
        g_kill.share_count++;
        
        if (g_kill.state == KILL_STATE_NORMAL) {
            g_kill.state = KILL_STATE_ARMED;
        }
    }
    
    int count = g_kill.share_count;
    
    pthread_mutex_unlock(&g_kill.share_lock);
    
    printf("[KILL] Share %d submitted (%d/%d)\n", 
           share->id, count, g_kill.config.threshold);
    
    return count;
}

void
kill_clear_shares(void)
{
    pthread_mutex_lock(&g_kill.share_lock);
    
    kill_secure_zero(g_kill.shares, sizeof(g_kill.shares));
    g_kill.share_count = 0;
    g_kill.state = KILL_STATE_NORMAL;
    
    pthread_mutex_unlock(&g_kill.share_lock);
    
    printf("[KILL] Shares cleared\n");
}

int
kill_activate(kill_command_t *command)
{
    if (!g_kill.initialized || !command) {
        return -1;
    }
    
    pthread_mutex_lock(&g_kill.share_lock);
    
    if (g_kill.share_count < g_kill.config.threshold) {
        pthread_mutex_unlock(&g_kill.share_lock);
        printf("[KILL] Not enough shares: %d/%d\n", 
               g_kill.share_count, g_kill.config.threshold);
        return -1;
    }
    
    /* Reconstruct secret */
    uint8_t secret[KILL_SECRET_SIZE];
    if (kill_combine_shares(g_kill.shares, g_kill.share_count, secret) != 0) {
        pthread_mutex_unlock(&g_kill.share_lock);
        return -1;
    }
    
    /* Build command */
    memcpy(command->magic, "KILL", 4);
    command->version = 1;
    command->timestamp = (uint64_t)time(NULL);
    memcpy(command->payload, secret, KILL_SECRET_SIZE);
    /* Signature would be computed here with private key */
    memset(command->signature, 0, sizeof(command->signature));
    
    g_kill.state = KILL_STATE_TRIGGERED;
    
    /* Secure zero */
    kill_secure_zero(secret, sizeof(secret));
    kill_secure_zero(g_kill.shares, sizeof(g_kill.shares));
    g_kill.share_count = 0;
    
    pthread_mutex_unlock(&g_kill.share_lock);
    
    printf("[KILL] ACTIVATED!\n");
    
    return 0;
}

int
kill_broadcast(const kill_command_t *command)
{
    if (!command) return -1;
    
    /* Would broadcast to all known agents */
    /* For now, just log */
    printf("[KILL] Broadcasting kill command to all agents\n");
    
    /* Return simulated count */
    return 10;
}

/* ==================== Dead Man's Switch ==================== */

int
kill_canary_publish(void)
{
    g_kill.canary_last_publish = time(NULL);
    /* Would publish to canary_url */
    printf("[KILL] Canary published\n");
    return 0;
}

int
kill_canary_check(canary_status_t *status)
{
    if (!status) return -1;
    
    time_t now = time(NULL);
    time_t age = now - g_kill.canary_last_seen;
    int hours = (int)(age / 3600);
    
    status->last_seen = g_kill.canary_last_seen;
    status->hours_remaining = g_kill.config.canary_expire - hours;
    status->alive = hours < g_kill.config.canary_expire;
    
    if (!status->alive && g_kill.state != KILL_STATE_SAFE_MODE) {
        kill_enter_safe_mode();
    }
    
    return 0;
}

void
kill_enter_safe_mode(void)
{
    g_kill.state = KILL_STATE_SAFE_MODE;
    printf("[KILL] SAFE MODE ACTIVATED - canary expired\n");
}

bool
kill_is_safe_mode(void)
{
    return g_kill.state == KILL_STATE_SAFE_MODE;
}

/* ==================== Agent Functions ==================== */

bool
kill_verify_command(const kill_command_t *command)
{
    if (!command) return false;
    
    /* Verify magic */
    if (memcmp(command->magic, "KILL", 4) != 0) {
        return false;
    }
    
    /* Verify version */
    if (command->version != 1) {
        return false;
    }
    
    /* Verify timestamp (not too old or in future) */
    time_t now = time(NULL);
    time_t cmd_time = (time_t)command->timestamp;
    if (cmd_time > now + 60 || now - cmd_time > 3600) {
        return false;  /* Expired or future */
    }
    
    /* Would verify signature here */
    
    return true;
}

void
kill_execute_shutdown(void)
{
    printf("[KILL] Executing shutdown...\n");
    /* Would stop all services and exit */
}
