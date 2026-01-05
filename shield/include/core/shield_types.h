/**
 * @file shield_types.h
 * @brief Core type definitions for SENTINEL Shield
 */

#ifndef SENTINEL_SHIELD_TYPES_H
#define SENTINEL_SHIELD_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ========================================================================= */
/*                              ERROR CODES                                   */
/* ========================================================================= */

typedef enum {
    SHIELD_OK = 0,
    SHIELD_ERR_INVALID = -1,
    SHIELD_ERR_MEMORY = -2,
    SHIELD_ERR_NETWORK = -3,
    SHIELD_ERR_TIMEOUT = -4,
    SHIELD_ERR_CONFIG = -5,
    SHIELD_ERR_NOT_FOUND = -6,
    SHIELD_ERR_ALREADY_EXISTS = -7,
    SHIELD_ERR_PERMISSION = -8,
    SHIELD_ERR_IO = -9,
    SHIELD_ERR_PARSE = -10,
    SHIELD_ERR_PROTOCOL = -11,
    SHIELD_ERR_INTERNAL = -99
} shield_err_t;

/* ========================================================================= */
/*                              COMMON TYPES                                  */
/* ========================================================================= */

typedef uint64_t shield_timestamp_t;
typedef uint32_t shield_id_t;

#endif /* SENTINEL_SHIELD_TYPES_H */
