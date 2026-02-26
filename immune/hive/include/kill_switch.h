/*
 * SENTINEL IMMUNE — Kill Switch Module
 * 
 * Decentralized emergency shutdown using Shamir's Secret Sharing.
 * Requires M-of-N authorized parties to activate kill switch.
 * 
 * Features:
 * - Shamir Secret Sharing over GF(256)
 * - Configurable threshold (default: 3-of-5)
 * - Dead Man's Switch (canary)
 * - Kill broadcast to all agents
 */

#ifndef IMMUNE_KILL_SWITCH_H
#define IMMUNE_KILL_SWITCH_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <time.h>

/* Configuration defaults */
#define KILL_DEFAULT_THRESHOLD      3
#define KILL_DEFAULT_SHARES         5
#define KILL_SECRET_SIZE            32      /* 256 bits */
#define KILL_SHARE_SIZE             33      /* 1 byte ID + 32 bytes data */
#define KILL_CANARY_HOURS           24      /* Publish every 24h */
#define KILL_CANARY_EXPIRE_HOURS    48      /* Safe mode after 48h */
#define KILL_MAX_SHARES             10      /* Maximum share holders */

/* Kill switch states */
typedef enum {
    KILL_STATE_NORMAL,      /* Normal operation */
    KILL_STATE_ARMED,       /* Shares being collected */
    KILL_STATE_TRIGGERED,   /* Kill activated */
    KILL_STATE_SAFE_MODE    /* Dead man's switch activated */
} kill_state_t;

/* Share holder information */
typedef struct {
    uint8_t     id;                 /* Share ID (1-255) */
    char        name[64];           /* Human-readable name */
    uint8_t     share[KILL_SHARE_SIZE];  /* The share data */
    time_t      created;            /* Creation timestamp */
    bool        valid;              /* Share is valid */
} kill_share_t;

/* Kill switch configuration */
typedef struct {
    int         threshold;          /* M shares needed to activate */
    int         total_shares;       /* N total shares generated */
    int         canary_hours;       /* Canary publish interval */
    int         canary_expire;      /* Hours until safe mode */
    char        canary_url[256];    /* Where to publish canary */
} kill_config_t;

/* Kill command (broadcast to agents) */
typedef struct {
    uint8_t     magic[4];           /* "KILL" */
    uint32_t    version;
    uint64_t    timestamp;
    uint8_t     signature[64];      /* Ed25519 signature */
    uint8_t     payload[32];        /* Kill code */
} kill_command_t;

/* Canary status */
typedef struct {
    time_t      last_seen;          /* Last canary timestamp */
    bool        alive;              /* Canary is alive */
    int         hours_remaining;    /* Before safe mode */
} canary_status_t;

/* === Configuration === */

/**
 * Initialize configuration with defaults.
 * @param config Configuration to initialize
 */
void kill_config_init(kill_config_t *config);

/* === Secret Sharing === */

/**
 * Generate N shares from a secret (Shamir's Secret Sharing).
 * @param secret The secret to split (KILL_SECRET_SIZE bytes)
 * @param shares Output array of shares (at least N elements)
 * @param n Number of shares to generate
 * @param m Threshold (shares needed to reconstruct)
 * @return 0 on success, -1 on error
 */
int kill_generate_shares(const uint8_t *secret,
                         kill_share_t *shares,
                         int n,
                         int m);

/**
 * Combine M shares to reconstruct the secret.
 * @param shares Array of M shares
 * @param m Number of shares provided
 * @param secret Output secret (KILL_SECRET_SIZE bytes)
 * @return 0 on success, -1 on error
 */
int kill_combine_shares(const kill_share_t *shares,
                        int m,
                        uint8_t *secret);

/**
 * Generate a random secret for the kill switch.
 * @param secret Output buffer (KILL_SECRET_SIZE bytes)
 * @return 0 on success, -1 on error
 */
int kill_generate_secret(uint8_t *secret);

/* === Kill Switch Control === */

/**
 * Initialize kill switch subsystem.
 * @param config Configuration
 * @return 0 on success, -1 on error
 */
int kill_init(const kill_config_t *config);

/**
 * Get current kill switch state.
 * @return Current state
 */
kill_state_t kill_get_state(void);

/**
 * Submit a share for kill switch activation.
 * @param share The share to submit
 * @return Number of shares collected, -1 on error
 */
int kill_submit_share(const kill_share_t *share);

/**
 * Clear all submitted shares (cancel activation).
 */
void kill_clear_shares(void);

/**
 * Activate kill switch (if enough shares collected).
 * @param command Output kill command (signed)
 * @return 0 on success, -1 if not enough shares
 */
int kill_activate(kill_command_t *command);

/**
 * Broadcast kill command to all agents.
 * @param command Signed kill command
 * @return Number of agents notified, -1 on error
 */
int kill_broadcast(const kill_command_t *command);

/* === Dead Man's Switch === */

/**
 * Publish canary (call periodically from Hive).
 * @return 0 on success, -1 on error
 */
int kill_canary_publish(void);

/**
 * Check canary status (call from Agent).
 * @param status Output canary status
 * @return 0 on success, -1 on error
 */
int kill_canary_check(canary_status_t *status);

/**
 * Enter safe mode (dead man's switch activated).
 */
void kill_enter_safe_mode(void);

/**
 * Check if in safe mode.
 * @return true if in safe mode
 */
bool kill_is_safe_mode(void);

/* === Agent Functions === */

/**
 * Agent: verify and process kill command.
 * @param command Received kill command
 * @return true if command is valid
 */
bool kill_verify_command(const kill_command_t *command);

/**
 * Agent: execute shutdown.
 */
void kill_execute_shutdown(void);

/* === Utility === */

/**
 * Get state name string.
 * @param state Kill state
 * @return State name
 */
const char* kill_state_string(kill_state_t state);

/**
 * Secure zero memory.
 * @param ptr Memory to zero
 * @param size Size in bytes
 */
void kill_secure_zero(void *ptr, size_t size);

#endif /* IMMUNE_KILL_SWITCH_H */
