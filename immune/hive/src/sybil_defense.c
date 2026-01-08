/*
 * SENTINEL IMMUNE — Sybil Defense Implementation
 * 
 * Protection against Sybil attacks using PoW, vouching, and trust.
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

#include "sybil_defense.h"

/* Simple SHA256 stub - in production use OpenSSL */
static void sha256(const void *data, size_t len, uint8_t *hash);

/* ==================== Constants ==================== */

#define MAX_AGENTS      1000
#define VOUCH_WEIGHT    0.1

/* ==================== Global State ==================== */

static struct {
    bool            initialized;
    sybil_agent_t   agents[MAX_AGENTS];
    int             agent_count;
    uint64_t        next_id;
    pthread_mutex_t lock;
} g_sybil = {0};

static const char* status_strings[] = {
    [AGENT_PENDING]     = "Pending",
    [AGENT_ACTIVE]      = "Active",
    [AGENT_SUSPECT]     = "Suspect",
    [AGENT_BLACKLISTED] = "Blacklisted"
};

const char*
agent_status_string(agent_status_t status)
{
    if (status >= 0 && status <= AGENT_BLACKLISTED) {
        return status_strings[status];
    }
    return "Unknown";
}

/* ==================== SHA256 Stub ==================== */

/* Simple hash for demo - use proper crypto in production */
static void
sha256(const void *data, size_t len, uint8_t *hash)
{
    /* FNV-1a based pseudo-hash for demo */
    uint64_t h1 = 0xcbf29ce484222325ULL;
    uint64_t h2 = 0x100000001b3ULL;
    const uint8_t *p = data;
    
    for (size_t i = 0; i < len; i++) {
        h1 ^= p[i];
        h1 *= 0x100000001b3ULL;
        h2 ^= p[i];
        h2 *= 0xcbf29ce484222325ULL;
    }
    
    /* Fill 32 bytes */
    memcpy(hash, &h1, 8);
    memcpy(hash + 8, &h2, 8);
    h1 = h1 ^ h2;
    h2 = h2 ^ (h1 >> 32);
    memcpy(hash + 16, &h1, 8);
    memcpy(hash + 24, &h2, 8);
}

/* ==================== Random ==================== */

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
    for (size_t i = 0; i < len; i++) {
        buf[i] = (uint8_t)(rand() & 0xFF);
    }
    return 0;
#endif
}

/* ==================== Lifecycle ==================== */

int
sybil_init(void)
{
    if (g_sybil.initialized) return 0;
    
    memset(&g_sybil, 0, sizeof(g_sybil));
    pthread_mutex_init(&g_sybil.lock, NULL);
    g_sybil.next_id = 1;
    g_sybil.initialized = true;
    
    printf("[SYBIL] Initialized (PoW difficulty: %d bits)\n", 
           SYBIL_POW_DIFFICULTY);
    
    return 0;
}

void
sybil_shutdown(void)
{
    if (!g_sybil.initialized) return;
    
    pthread_mutex_destroy(&g_sybil.lock);
    memset(&g_sybil, 0, sizeof(g_sybil));
    g_sybil.initialized = false;
}

/* ==================== Proof of Work ==================== */

int
sybil_generate_puzzle(sybil_puzzle_t *puzzle)
{
    if (!puzzle) return -1;
    
    secure_random(puzzle->challenge, 32);
    puzzle->difficulty = SYBIL_POW_DIFFICULTY;
    puzzle->expires = time(NULL) + 300;  /* 5 minute expiry */
    
    return 0;
}

/* Count leading zero bits */
static int
count_leading_zeros(const uint8_t *hash)
{
    int zeros = 0;
    for (int i = 0; i < 32; i++) {
        if (hash[i] == 0) {
            zeros += 8;
        } else {
            /* Count leading zeros in this byte */
            uint8_t b = hash[i];
            while ((b & 0x80) == 0) {
                zeros++;
                b <<= 1;
            }
            break;
        }
    }
    return zeros;
}

int
sybil_solve_pow(const sybil_puzzle_t *puzzle, sybil_solution_t *solution)
{
    if (!puzzle || !solution) return -1;
    
    memcpy(solution->challenge, puzzle->challenge, 32);
    
    uint8_t data[40];  /* 32 challenge + 8 nonce */
    memcpy(data, puzzle->challenge, 32);
    
    uint64_t nonce = 0;
    time_t start = time(NULL);
    
    while (1) {
        /* Copy nonce */
        memcpy(data + 32, &nonce, 8);
        
        /* Hash */
        sha256(data, 40, solution->hash);
        
        /* Check difficulty */
        if (count_leading_zeros(solution->hash) >= (int)puzzle->difficulty) {
            solution->nonce = nonce;
            printf("[SYBIL] PoW solved in %ld seconds (nonce: %lu)\n",
                   time(NULL) - start, nonce);
            return 0;
        }
        
        nonce++;
        
        /* Check expiry */
        if (time(NULL) > puzzle->expires) {
            return -1;  /* Expired */
        }
    }
}

bool
sybil_verify_pow(const sybil_puzzle_t *puzzle, const sybil_solution_t *solution)
{
    if (!puzzle || !solution) return false;
    
    /* Verify challenge matches */
    if (memcmp(puzzle->challenge, solution->challenge, 32) != 0) {
        return false;
    }
    
    /* Recompute hash */
    uint8_t data[40];
    uint8_t hash[32];
    
    memcpy(data, solution->challenge, 32);
    memcpy(data + 32, &solution->nonce, 8);
    sha256(data, 40, hash);
    
    /* Verify hash matches */
    if (memcmp(hash, solution->hash, 32) != 0) {
        return false;
    }
    
    /* Verify difficulty */
    return count_leading_zeros(hash) >= (int)puzzle->difficulty;
}

/* ==================== Agent Management ==================== */

int
sybil_register_agent(const uint8_t *pubkey, sybil_agent_t *agent)
{
    if (!pubkey || !agent) return -1;
    
    pthread_mutex_lock(&g_sybil.lock);
    
    if (g_sybil.agent_count >= MAX_AGENTS) {
        pthread_mutex_unlock(&g_sybil.lock);
        return -1;
    }
    
    sybil_agent_t *a = &g_sybil.agents[g_sybil.agent_count];
    memset(a, 0, sizeof(*a));
    
    a->id = g_sybil.next_id++;
    memcpy(a->pubkey, pubkey, 32);
    a->trust = SYBIL_INITIAL_TRUST;
    a->joined = time(NULL);
    a->status = AGENT_PENDING;
    
    g_sybil.agent_count++;
    
    memcpy(agent, a, sizeof(*agent));
    
    pthread_mutex_unlock(&g_sybil.lock);
    
    printf("[SYBIL] Agent %lu registered (pending)\n", a->id);
    
    return 0;
}

sybil_agent_t*
sybil_get_agent(uint64_t id)
{
    for (int i = 0; i < g_sybil.agent_count; i++) {
        if (g_sybil.agents[i].id == id) {
            return &g_sybil.agents[i];
        }
    }
    return NULL;
}

void
sybil_update_trust(uint64_t id, double delta)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    sybil_agent_t *a = sybil_get_agent(id);
    if (a) {
        a->trust += delta;
        if (a->trust < 0) a->trust = 0;
        if (a->trust > SYBIL_MAX_TRUST) a->trust = SYBIL_MAX_TRUST;
    }
    
    pthread_mutex_unlock(&g_sybil.lock);
}

void
sybil_apply_decay(void)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    time_t now = time(NULL);
    
    for (int i = 0; i < g_sybil.agent_count; i++) {
        sybil_agent_t *a = &g_sybil.agents[i];
        if (a->status == AGENT_ACTIVE) {
            double days = (double)(now - a->joined) / 86400.0;
            double decay = days * SYBIL_DECAY_RATE;
            a->trust = SYBIL_INITIAL_TRUST + 
                       (a->trust - SYBIL_INITIAL_TRUST) * (1.0 - decay);
            if (a->trust < 0.1) a->trust = 0.1;
        }
    }
    
    pthread_mutex_unlock(&g_sybil.lock);
}

/* ==================== Vouching ==================== */

int
sybil_request_vouch(uint64_t target_id)
{
    sybil_agent_t *a = sybil_get_agent(target_id);
    if (!a) return -1;
    
    printf("[SYBIL] Agent %lu requesting vouches (%d/%d)\n",
           target_id, a->vouches_received, SYBIL_VOUCHES_REQUIRED);
    
    return a->vouches_received;
}

int
sybil_grant_vouch(uint64_t voucher_id, uint64_t target_id)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    sybil_agent_t *voucher = sybil_get_agent(voucher_id);
    sybil_agent_t *target = sybil_get_agent(target_id);
    
    if (!voucher || !target) {
        pthread_mutex_unlock(&g_sybil.lock);
        return -1;
    }
    
    if (voucher->status != AGENT_ACTIVE || voucher->trust < SYBIL_CONSENSUS_THRESH) {
        pthread_mutex_unlock(&g_sybil.lock);
        return -1;  /* Voucher not trusted enough */
    }
    
    target->vouches_received++;
    target->trust += VOUCH_WEIGHT * voucher->trust;
    voucher->vouches_given++;
    
    /* Check if promoted to active */
    if (target->vouches_received >= SYBIL_VOUCHES_REQUIRED &&
        target->status == AGENT_PENDING) {
        target->status = AGENT_ACTIVE;
        printf("[SYBIL] Agent %lu promoted to ACTIVE\n", target_id);
    }
    
    int vouches = target->vouches_received;
    
    pthread_mutex_unlock(&g_sybil.lock);
    
    return vouches;
}

int
sybil_revoke_vouch(uint64_t voucher_id, uint64_t target_id)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    sybil_agent_t *voucher = sybil_get_agent(voucher_id);
    sybil_agent_t *target = sybil_get_agent(target_id);
    
    if (!voucher || !target) {
        pthread_mutex_unlock(&g_sybil.lock);
        return -1;
    }
    
    if (target->vouches_received > 0) {
        target->vouches_received--;
        target->trust -= VOUCH_WEIGHT * voucher->trust;
        if (target->trust < 0) target->trust = 0;
    }
    
    int vouches = target->vouches_received;
    
    pthread_mutex_unlock(&g_sybil.lock);
    
    return vouches;
}

/* ==================== Reporting ==================== */

void
sybil_report_agent(uint64_t reporter_id, uint64_t target_id, const char *reason)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    sybil_agent_t *reporter = sybil_get_agent(reporter_id);
    sybil_agent_t *target = sybil_get_agent(target_id);
    
    if (!reporter || !target) {
        pthread_mutex_unlock(&g_sybil.lock);
        return;
    }
    
    target->reports_against++;
    target->trust -= 0.1 * reporter->trust;
    
    if (target->trust < 0.2 || target->reports_against >= 5) {
        target->status = AGENT_SUSPECT;
    }
    
    printf("[SYBIL] Agent %lu reported by %lu: %s\n",
           target_id, reporter_id, reason ? reason : "no reason");
    
    pthread_mutex_unlock(&g_sybil.lock);
}

void
sybil_blacklist(uint64_t id)
{
    pthread_mutex_lock(&g_sybil.lock);
    
    sybil_agent_t *a = sybil_get_agent(id);
    if (a) {
        a->status = AGENT_BLACKLISTED;
        a->trust = 0;
        printf("[SYBIL] Agent %lu BLACKLISTED\n", id);
    }
    
    pthread_mutex_unlock(&g_sybil.lock);
}

bool
sybil_is_blacklisted(uint64_t id)
{
    sybil_agent_t *a = sybil_get_agent(id);
    return a && a->status == AGENT_BLACKLISTED;
}

/* ==================== Trust ==================== */

double
sybil_get_trust(uint64_t id)
{
    sybil_agent_t *a = sybil_get_agent(id);
    return a ? a->trust : 0.0;
}

bool
sybil_can_vote(uint64_t id)
{
    sybil_agent_t *a = sybil_get_agent(id);
    if (!a) return false;
    
    return a->status == AGENT_ACTIVE && 
           a->trust >= SYBIL_CONSENSUS_THRESH;
}
