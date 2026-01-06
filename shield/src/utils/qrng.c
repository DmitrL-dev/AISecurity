/**
 * @file qrng.c
 * @brief Quantum Random Number Generator Implementation
 * 
 * Implements QRNG with simulated quantum backend using:
 * - Quantum state vector evolution
 * - Hadamard transform for superposition
 * - Measurement collapse with environmental decoherence
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#include <wincrypt.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

#include "shield_qrng.h"

/* ============================================================================
 * Constants
 * ============================================================================ */

#define QRNG_POOL_DEFAULT_SIZE  4096    /* Default entropy pool size */
#define QRNG_DECOHERENCE_FACTOR 0.02    /* Environmental noise factor */
#define QRNG_SEED_REFRESH_MS    60000   /* Reseed interval */

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ============================================================================
 * Complex Number Type (for quantum state)
 * ============================================================================ */

typedef struct complex {
    double re;  /* Real part */
    double im;  /* Imaginary part */
} complex_t;

/* Complex operations */
static inline complex_t complex_add(complex_t a, complex_t b) {
    return (complex_t){a.re + b.re, a.im + b.im};
}

static inline complex_t complex_mul(complex_t a, complex_t b) {
    return (complex_t){
        a.re * b.re - a.im * b.im,
        a.re * b.im + a.im * b.re
    };
}

static inline complex_t complex_scale(complex_t a, double s) {
    return (complex_t){a.re * s, a.im * s};
}

static inline double complex_prob(complex_t a) {
    return a.re * a.re + a.im * a.im;
}

/* ============================================================================
 * Global State
 * ============================================================================ */

static struct {
    bool            initialized;
    qrng_config_t   config;
    qrng_stats_t    stats;
    
    /* Entropy pool */
    uint8_t        *pool;
    size_t          pool_size;
    size_t          pool_pos;
    
    /* Quantum state for simulation */
    uint64_t        quantum_seed;
    double          phase_accumulator;
    
    /* System entropy source */
#ifdef _WIN32
    HCRYPTPROV      crypt_prov;
#else
    int             urandom_fd;
#endif
} g_qrng = {0};

/* ============================================================================
 * Platform-specific System Entropy
 * ============================================================================ */

static shield_err_t get_system_entropy(void *buf, size_t len) {
#ifdef _WIN32
    if (!CryptGenRandom(g_qrng.crypt_prov, (DWORD)len, (BYTE *)buf)) {
        return SHIELD_ERR_INTERNAL;
    }
    return SHIELD_OK;
#else
    ssize_t rd = read(g_qrng.urandom_fd, buf, len);
    if (rd < 0 || (size_t)rd != len) {
        return SHIELD_ERR_INTERNAL;
    }
    return SHIELD_OK;
#endif
}

static shield_err_t init_system_entropy(void) {
#ifdef _WIN32
    if (!CryptAcquireContext(&g_qrng.crypt_prov, NULL, NULL, 
                              PROV_RSA_FULL, CRYPT_VERIFYCONTEXT)) {
        return SHIELD_ERR_INTERNAL;
    }
#else
    g_qrng.urandom_fd = open("/dev/urandom", O_RDONLY);
    if (g_qrng.urandom_fd < 0) {
        return SHIELD_ERR_INTERNAL;
    }
#endif
    return SHIELD_OK;
}

static void cleanup_system_entropy(void) {
#ifdef _WIN32
    if (g_qrng.crypt_prov) {
        CryptReleaseContext(g_qrng.crypt_prov, 0);
        g_qrng.crypt_prov = 0;
    }
#else
    if (g_qrng.urandom_fd >= 0) {
        close(g_qrng.urandom_fd);
        g_qrng.urandom_fd = -1;
    }
#endif
}

/* ============================================================================
 * Quantum Simulation Backend
 * ============================================================================ */

/**
 * @brief Apply Hadamard gate to qubit state
 * 
 * H|0⟩ = (|0⟩ + |1⟩) / √2
 * H|1⟩ = (|0⟩ - |1⟩) / √2
 */
static void hadamard_gate(complex_t state[2]) {
    const double inv_sqrt2 = 1.0 / sqrt(2.0);
    complex_t new_state[2];
    
    new_state[0] = complex_scale(complex_add(state[0], state[1]), inv_sqrt2);
    new_state[1] = complex_scale(
        (complex_t){state[0].re - state[1].re, state[0].im - state[1].im}, 
        inv_sqrt2
    );
    
    state[0] = new_state[0];
    state[1] = new_state[1];
}

/**
 * @brief Apply phase rotation gate
 * 
 * Rz(θ)|ψ⟩ = e^(-iθ/2)|0⟩⟨0|ψ⟩ + e^(iθ/2)|1⟩⟨1|ψ⟩
 */
static void phase_gate(complex_t state[2], double theta) {
    double half_theta = theta / 2.0;
    complex_t phase0 = {cos(-half_theta), sin(-half_theta)};
    complex_t phase1 = {cos(half_theta), sin(half_theta)};
    
    state[0] = complex_mul(state[0], phase0);
    state[1] = complex_mul(state[1], phase1);
}

/**
 * @brief Apply decoherence (environmental noise)
 * 
 * Simulates thermal noise and interaction with environment
 */
static void apply_decoherence(complex_t state[2], double noise_factor) {
    /* Get small random perturbation from system entropy */
    uint32_t noise_bits;
    get_system_entropy(&noise_bits, sizeof(noise_bits));
    
    double noise = ((double)(noise_bits & 0xFFFF) / 65535.0 - 0.5) * noise_factor;
    
    /* Apply amplitude damping */
    double damping = 1.0 - fabs(noise) * 0.1;
    state[0] = complex_scale(state[0], damping);
    state[1] = complex_scale(state[1], damping);
    
    /* Renormalize */
    double norm = sqrt(complex_prob(state[0]) + complex_prob(state[1]));
    if (norm > 0) {
        state[0] = complex_scale(state[0], 1.0 / norm);
        state[1] = complex_scale(state[1], 1.0 / norm);
    }
    
    /* Apply phase noise */
    phase_gate(state, noise * M_PI);
}

/**
 * @brief Generate a quantum random bit
 * 
 * 1. Initialize qubit in |0⟩
 * 2. Apply Hadamard to create superposition
 * 3. Apply environmental decoherence
 * 4. Measure (collapse) to |0⟩ or |1⟩
 */
static uint8_t quantum_bit(void) {
    /* Initialize |0⟩ state */
    complex_t state[2] = {
        {1.0, 0.0},  /* |0⟩ amplitude */
        {0.0, 0.0}   /* |1⟩ amplitude */
    };
    
    /* Apply Hadamard: |0⟩ → |+⟩ = (|0⟩ + |1⟩)/√2 */
    hadamard_gate(state);
    
    /* Add phase based on accumulated quantum phase */
    g_qrng.phase_accumulator += 0.1;
    phase_gate(state, g_qrng.phase_accumulator);
    
    /* Apply environmental decoherence */
    apply_decoherence(state, QRNG_DECOHERENCE_FACTOR);
    
    /* Measurement: calculate probability of |0⟩ */
    double p0 = complex_prob(state[0]);
    
    /* Get random value for measurement collapse */
    uint32_t r;
    get_system_entropy(&r, sizeof(r));
    double rand_val = (double)r / (double)UINT32_MAX;
    
    /* Collapse: if rand < P(|0⟩), measure 0; else measure 1 */
    return (rand_val >= p0) ? 1 : 0;
}

/**
 * @brief Generate a quantum random byte (8 bits)
 */
static uint8_t quantum_byte(void) {
    uint8_t result = 0;
    for (int i = 0; i < 8; i++) {
        result = (result << 1) | quantum_bit();
    }
    return result;
}

/**
 * @brief Fill buffer with quantum random bytes
 */
static void fill_quantum_bytes(void *buf, size_t len) {
    uint8_t *p = (uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        p[i] = quantum_byte();
    }
}

/* ============================================================================
 * Entropy Pool Management
 * ============================================================================ */

static shield_err_t refill_pool(void) {
    if (!g_qrng.pool) return SHIELD_ERR_INVALID;
    
    switch (g_qrng.config.backend) {
        case QRNG_BACKEND_SIMULATED:
        case QRNG_BACKEND_AUTO:
            fill_quantum_bytes(g_qrng.pool, g_qrng.pool_size);
            break;
            
        case QRNG_BACKEND_SYSTEM:
            get_system_entropy(g_qrng.pool, g_qrng.pool_size);
            break;
            
        case QRNG_BACKEND_REMOTE:
            /* TODO: Implement remote API fetch */
            /* Fallback to simulated for now */
            fill_quantum_bytes(g_qrng.pool, g_qrng.pool_size);
            g_qrng.stats.fallbacks++;
            break;
            
        case QRNG_BACKEND_HARDWARE:
            /* TODO: Implement hardware QRNG */
            fill_quantum_bytes(g_qrng.pool, g_qrng.pool_size);
            g_qrng.stats.fallbacks++;
            break;
    }
    
    g_qrng.pool_pos = 0;
    return SHIELD_OK;
}

static shield_err_t get_from_pool(void *buf, size_t len) {
    uint8_t *out = (uint8_t *)buf;
    size_t remaining = len;
    
    while (remaining > 0) {
        /* Refill pool if exhausted */
        if (g_qrng.pool_pos >= g_qrng.pool_size) {
            shield_err_t err = refill_pool();
            if (err != SHIELD_OK) return err;
        }
        
        /* Copy from pool */
        size_t available = g_qrng.pool_size - g_qrng.pool_pos;
        size_t to_copy = (remaining < available) ? remaining : available;
        
        memcpy(out, g_qrng.pool + g_qrng.pool_pos, to_copy);
        
        g_qrng.pool_pos += to_copy;
        out += to_copy;
        remaining -= to_copy;
    }
    
    return SHIELD_OK;
}

/* ============================================================================
 * Public API Implementation
 * ============================================================================ */

shield_err_t shield_qrng_init(const qrng_config_t *config) {
    if (g_qrng.initialized) {
        return SHIELD_OK; /* Already initialized */
    }
    
    /* Initialize system entropy first */
    shield_err_t err = init_system_entropy();
    if (err != SHIELD_OK) {
        return err;
    }
    
    /* Apply configuration */
    if (config) {
        memcpy(&g_qrng.config, config, sizeof(qrng_config_t));
    } else {
        /* Defaults */
        g_qrng.config.backend = QRNG_BACKEND_AUTO;
        g_qrng.config.pool_size = QRNG_POOL_DEFAULT_SIZE;
        g_qrng.config.fallback_enabled = true;
        g_qrng.config.refresh_interval_ms = QRNG_SEED_REFRESH_MS;
    }
    
    /* Allocate entropy pool */
    g_qrng.pool_size = g_qrng.config.pool_size > 0 
                       ? g_qrng.config.pool_size 
                       : QRNG_POOL_DEFAULT_SIZE;
    g_qrng.pool = malloc(g_qrng.pool_size);
    if (!g_qrng.pool) {
        cleanup_system_entropy();
        return SHIELD_ERR_NOMEM;
    }
    
    /* Initialize quantum state */
    get_system_entropy(&g_qrng.quantum_seed, sizeof(g_qrng.quantum_seed));
    g_qrng.phase_accumulator = 0.0;
    
    /* Initial pool fill */
    g_qrng.pool_pos = g_qrng.pool_size; /* Force refill */
    err = refill_pool();
    if (err != SHIELD_OK) {
        free(g_qrng.pool);
        cleanup_system_entropy();
        return err;
    }
    
    /* Set active backend */
    if (g_qrng.config.backend == QRNG_BACKEND_AUTO) {
        g_qrng.stats.active_backend = QRNG_BACKEND_SIMULATED;
    } else {
        g_qrng.stats.active_backend = g_qrng.config.backend;
    }
    
    g_qrng.initialized = true;
    return SHIELD_OK;
}

void shield_qrng_shutdown(void) {
    if (!g_qrng.initialized) return;
    
    /* Secure wipe pool */
    if (g_qrng.pool) {
        memset(g_qrng.pool, 0, g_qrng.pool_size);
        free(g_qrng.pool);
        g_qrng.pool = NULL;
    }
    
    cleanup_system_entropy();
    
    memset(&g_qrng, 0, sizeof(g_qrng));
}

shield_err_t shield_qrng_bytes(void *buf, size_t len) {
    if (!g_qrng.initialized) {
        /* Auto-init with defaults */
        shield_err_t err = shield_qrng_init(NULL);
        if (err != SHIELD_OK) return err;
    }
    
    if (!buf || len == 0) return SHIELD_ERR_INVALID;
    
    shield_err_t err = get_from_pool(buf, len);
    if (err == SHIELD_OK) {
        g_qrng.stats.bytes_generated += len;
        g_qrng.stats.requests++;
    }
    
    return err;
}

uint64_t shield_qrng_u64(void) {
    uint64_t val;
    shield_qrng_bytes(&val, sizeof(val));
    return val;
}

uint32_t shield_qrng_u32(void) {
    uint32_t val;
    shield_qrng_bytes(&val, sizeof(val));
    return val;
}

uint64_t shield_qrng_range(uint64_t max) {
    if (max == 0) return 0;
    if (max == 1) return 0;
    
    /* Avoid modulo bias by rejection sampling */
    uint64_t threshold = UINT64_MAX - (UINT64_MAX % max);
    uint64_t val;
    
    do {
        val = shield_qrng_u64();
    } while (val >= threshold);
    
    return val % max;
}

double shield_qrng_float(void) {
    /* Generate double in [0, 1) using 53 bits of randomness */
    uint64_t val = shield_qrng_u64();
    return (val >> 11) * (1.0 / 9007199254740992.0);  /* 2^53 */
}

void shield_qrng_get_stats(qrng_stats_t *stats) {
    if (!stats) return;
    memcpy(stats, &g_qrng.stats, sizeof(qrng_stats_t));
}

float shield_qrng_entropy_quality(void) {
    /* Estimate entropy using byte frequency analysis */
    if (!g_qrng.pool || g_qrng.pool_pos == 0) {
        return 8.0f; /* Assume max entropy if no data */
    }
    
    size_t sample_size = g_qrng.pool_pos < 256 ? g_qrng.pool_pos : 256;
    uint32_t freq[256] = {0};
    
    for (size_t i = 0; i < sample_size; i++) {
        freq[g_qrng.pool[i]]++;
    }
    
    /* Shannon entropy */
    double entropy = 0.0;
    for (int i = 0; i < 256; i++) {
        if (freq[i] > 0) {
            double p = (double)freq[i] / (double)sample_size;
            entropy -= p * log2(p);
        }
    }
    
    g_qrng.stats.estimated_entropy = (float)entropy;
    return (float)entropy;
}

shield_err_t shield_qrng_refresh_pool(void) {
    if (!g_qrng.initialized) return SHIELD_ERR_INVALID;
    return refill_pool();
}

const char *qrng_backend_name(qrng_backend_t backend) {
    switch (backend) {
        case QRNG_BACKEND_AUTO:      return "auto";
        case QRNG_BACKEND_SIMULATED: return "simulated";
        case QRNG_BACKEND_REMOTE:    return "remote";
        case QRNG_BACKEND_HARDWARE:  return "hardware";
        case QRNG_BACKEND_SYSTEM:    return "system";
        default:                     return "unknown";
    }
}
