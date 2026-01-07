/**
 * @file safe_memory.h
 * @brief IMMUNE Safe Memory Management
 * 
 * Memory allocation wrappers that prevent common vulnerabilities:
 * - Use-after-free (pointers nullified after free)
 * - Double-free (NULL check before free)
 * - Uninitialized memory (zero-initialization)
 * - Buffer overflow (size checks)
 * 
 * @author SENTINEL R&D
 * @date 2026-01-07
 */

#ifndef IMMUNE_SAFE_MEMORY_H
#define IMMUNE_SAFE_MEMORY_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Configuration
 * ============================================================================ */

/** Maximum single allocation size (16 MB default) */
#ifndef SAFE_MAX_ALLOC_SIZE
#define SAFE_MAX_ALLOC_SIZE (16 * 1024 * 1024)
#endif

/** Enable memory poisoning on free (development builds) */
#ifndef SAFE_POISON_ON_FREE
#ifdef DEBUG
#define SAFE_POISON_ON_FREE 1
#else
#define SAFE_POISON_ON_FREE 0
#endif
#endif

/** Poison byte pattern */
#define SAFE_POISON_BYTE 0xDE

/* ============================================================================
 * Allocation Functions
 * ============================================================================ */

/**
 * @brief Allocate memory with zero-initialization
 * 
 * @param size Number of bytes to allocate
 * @return Pointer to allocated memory, or NULL on failure
 * 
 * @note Memory is always zero-initialized
 * @note Returns NULL if size is 0 or exceeds SAFE_MAX_ALLOC_SIZE
 */
void* safe_alloc(size_t size);

/**
 * @brief Allocate array with overflow check
 * 
 * @param count Number of elements
 * @param elem_size Size of each element
 * @return Pointer to allocated memory, or NULL on failure
 * 
 * @note Checks for integer overflow (count * elem_size)
 * @note Memory is always zero-initialized
 */
void* safe_calloc(size_t count, size_t elem_size);

/**
 * @brief Reallocate memory with safety checks
 * 
 * @param ptr Pointer to existing allocation (can be NULL)
 * @param new_size New size in bytes
 * @return Pointer to reallocated memory, or NULL on failure
 * 
 * @note If reallocation fails, original pointer remains valid
 * @note New memory (if larger) is zero-initialized
 */
void* safe_realloc(void* ptr, size_t new_size);

/**
 * @brief Free memory and nullify pointer
 * 
 * @param pptr Pointer to pointer (will be set to NULL)
 * 
 * @note Safe to call with NULL or pointer to NULL
 * @note If SAFE_POISON_ON_FREE is enabled, memory is poisoned before free
 */
void safe_free(void** pptr);

/**
 * @brief Free memory with known size (enables poisoning)
 * 
 * @param pptr Pointer to pointer (will be set to NULL)
 * @param size Size of allocation (for poisoning)
 */
void safe_free_size(void** pptr, size_t size);

/* ============================================================================
 * Convenience Macros
 * ============================================================================ */

/**
 * @brief Type-safe allocation
 * 
 * Example: struct foo* p = SAFE_NEW(struct foo);
 */
#define SAFE_NEW(type) ((type*)safe_alloc(sizeof(type)))

/**
 * @brief Type-safe array allocation
 * 
 * Example: int* arr = SAFE_NEW_ARRAY(int, 100);
 */
#define SAFE_NEW_ARRAY(type, count) ((type*)safe_calloc(count, sizeof(type)))

/**
 * @brief Free and nullify pointer
 * 
 * Example: SAFE_FREE(ptr);
 */
#define SAFE_FREE(ptr) safe_free((void**)&(ptr))

/**
 * @brief Free with size and nullify pointer
 * 
 * Example: SAFE_FREE_SIZE(ptr, sizeof(*ptr));
 */
#define SAFE_FREE_SIZE(ptr, size) safe_free_size((void**)&(ptr), (size))

/* ============================================================================
 * String Functions (Safe Alternatives)
 * ============================================================================ */

/**
 * @brief Safe string copy (BSD strlcpy)
 * 
 * @param dst Destination buffer
 * @param src Source string
 * @param dst_size Size of destination buffer
 * @return Length of src (truncated if > dst_size - 1)
 * 
 * @note Always null-terminates (unless dst_size is 0)
 * @note Returns 0 if dst or src is NULL
 */
size_t safe_strcpy(char* dst, const char* src, size_t dst_size);

/**
 * @brief Safe string concatenation (BSD strlcat)
 * 
 * @param dst Destination buffer
 * @param src Source string to append
 * @param dst_size Size of destination buffer
 * @return Length of attempted string (dst + src)
 * 
 * @note Always null-terminates
 */
size_t safe_strcat(char* dst, const char* src, size_t dst_size);

/**
 * @brief Safe sprintf
 * 
 * @param dst Destination buffer
 * @param dst_size Size of destination buffer
 * @param fmt Format string
 * @param ... Format arguments
 * @return Number of characters written (excluding null), or -1 on error
 * 
 * @note Always null-terminates
 * @note Returns -1 if dst is NULL or dst_size is 0
 */
int safe_sprintf(char* dst, size_t dst_size, const char* fmt, ...)
    __attribute__((format(printf, 3, 4)));

/**
 * @brief Duplicate string with bounds check
 * 
 * @param src Source string
 * @param max_len Maximum length to copy (excluding null)
 * @return Newly allocated string, or NULL on failure
 * 
 * @note Caller must free with SAFE_FREE
 */
char* safe_strdup(const char* src, size_t max_len);

/* ============================================================================
 * Buffer Operations
 * ============================================================================ */

/**
 * @brief Safe memory copy with overlap detection
 * 
 * @param dst Destination buffer
 * @param dst_size Size of destination buffer
 * @param src Source buffer
 * @param count Number of bytes to copy
 * @return true on success, false on error (null ptr, overflow, overlap)
 */
bool safe_memcpy(void* dst, size_t dst_size, const void* src, size_t count);

/**
 * @brief Safe memory move (handles overlap)
 * 
 * @param dst Destination buffer
 * @param dst_size Size of destination buffer
 * @param src Source buffer
 * @param count Number of bytes to move
 * @return true on success, false on error
 */
bool safe_memmove(void* dst, size_t dst_size, const void* src, size_t count);

/**
 * @brief Zero out sensitive memory (resistant to optimization)
 * 
 * @param ptr Pointer to memory
 * @param size Number of bytes to zero
 * 
 * @note Uses volatile to prevent compiler optimization
 */
void safe_memzero(void* ptr, size_t size);

/* ============================================================================
 * Validation Helpers
 * ============================================================================ */

/**
 * @brief Check for integer multiplication overflow
 * 
 * @param a First operand
 * @param b Second operand
 * @param result Pointer to store result (if no overflow)
 * @return true if no overflow, false if overflow would occur
 */
bool safe_mul_size(size_t a, size_t b, size_t* result);

/**
 * @brief Check for integer addition overflow
 * 
 * @param a First operand
 * @param b Second operand
 * @param result Pointer to store result (if no overflow)
 * @return true if no overflow, false if overflow would occur
 */
bool safe_add_size(size_t a, size_t b, size_t* result);

#ifdef __cplusplus
}
#endif

#endif /* IMMUNE_SAFE_MEMORY_H */
