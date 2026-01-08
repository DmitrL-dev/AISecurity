/*
 * SENTINEL IMMUNE — Sybil Defense Module
 * 
 * Protection against Sybil attacks in HERD network.
 * Uses Proof-of-Work, vouching, and trust scoring.
 */

#ifndef IMMUNE_SYBIL_DEFENSE_H
#define IMMUNE_SYBIL_DEFENSE_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

/* Configuration */
#define SYBIL_POW_DIFFICULTY    20      /* Leading zero bits */
#define SYBIL_VOUCHES_REQUIRED  3       /* Vouches needed to join */
#define SYBIL_INITIAL_TRUST     0.3     /* New agent trust */
#define SYBIL_MAX_TRUST         1.0
#define SYBIL_DECAY_RATE        0.01    /* Trust decay per day */
#define SYBIL_CONSENSUS_THRESH  0.5     /* Min trust for voting */

/* Agent status */
typedef enum {
    AGENT_PENDING,      /* Awaiting vouches */
    AGENT_ACTIVE,       /* Full member */
    AGENT_SUSPECT,      /* Under review */
    AGENT_BLACKLISTED   /* Banned */
} agent_status_t;

/* Agent identity */
typedef struct {
    uint64_t        id;
    uint8_t         pubkey[32];
    double          trust;
    time_t          joined;
    int             vouches_received;
    int             vouches_given;
    int             reports_against;
    agent_status_t  status;
} sybil_agent_t;

/* PoW puzzle */
typedef struct {
    uint8_t     challenge[32];
    uint32_t    difficulty;
    time_t      expires;
} sybil_puzzle_t;

/* PoW solution */
typedef struct {
    uint8_t     challenge[32];
    uint64_t    nonce;
    uint8_t     hash[32];
} sybil_solution_t;

/* === Lifecycle === */

int sybil_init(void);
void sybil_shutdown(void);

/* === Proof of Work === */

int sybil_generate_puzzle(sybil_puzzle_t *puzzle);
int sybil_solve_pow(const sybil_puzzle_t *puzzle, sybil_solution_t *solution);
bool sybil_verify_pow(const sybil_puzzle_t *puzzle, const sybil_solution_t *solution);

/* === Agent Management === */

int sybil_register_agent(const uint8_t *pubkey, sybil_agent_t *agent);
sybil_agent_t* sybil_get_agent(uint64_t id);
void sybil_update_trust(uint64_t id, double delta);
void sybil_apply_decay(void);

/* === Vouching === */

int sybil_request_vouch(uint64_t target_id);
int sybil_grant_vouch(uint64_t voucher_id, uint64_t target_id);
int sybil_revoke_vouch(uint64_t voucher_id, uint64_t target_id);

/* === Reporting === */

void sybil_report_agent(uint64_t reporter_id, uint64_t target_id, const char *reason);
void sybil_blacklist(uint64_t id);
bool sybil_is_blacklisted(uint64_t id);

/* === Trust === */

double sybil_get_trust(uint64_t id);
bool sybil_can_vote(uint64_t id);

/* === Utility === */

const char* agent_status_string(agent_status_t status);

#endif /* IMMUNE_SYBIL_DEFENSE_H */
