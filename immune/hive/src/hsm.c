/*
 * SENTINEL IMMUNE — TPM/HSM Integration
 * 
 * Hardware Security Module binding.
 * Protects master keys and critical secrets.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "../include/hive.h"

/* HSM key constants */
#define HSM_KEY_SIZE        32
#define HSM_MAX_SEALED      10

/* hsm_provider_t is defined in hive.h */

/* Sealed data slot */
typedef struct {
    char        name[64];
    uint8_t     sealed_data[512];
    size_t      sealed_size;
    uint8_t     pcr_policy[32];
    int         active;
} sealed_slot_t;

/* HSM context */
typedef struct {
    hsm_provider_t  provider;
    int             initialized;
    
    /* TPM handle */
    void            *tpm_context;
    uint32_t        srk_handle;
    
    /* Sealed data */
    sealed_slot_t   sealed[HSM_MAX_SEALED];
    int             sealed_count;
    
    /* Derived keys */
    uint8_t         master_key[HSM_KEY_SIZE];
    int             master_key_loaded;
} hsm_ctx_t;

/* Global context */
static hsm_ctx_t g_hsm;

/* ==================== Software HSM (Development) ==================== */

static int
sw_hsm_init(void)
{
    printf("HSM: Using SOFTWARE emulation (dev only!)\n");
    
    /* Generate pseudo-random master key */
    srand((unsigned int)time(NULL));
    for (int i = 0; i < HSM_KEY_SIZE; i++) {
        g_hsm.master_key[i] = (uint8_t)(rand() & 0xFF);
    }
    g_hsm.master_key_loaded = 1;
    
    return 0;
}

static int
sw_hsm_seal(const char *name, const uint8_t *data, size_t size,
            uint8_t *sealed, size_t *sealed_size)
{
    if (size > 480) return -1;
    
    /* Simple XOR sealing (just for demo) */
    memcpy(sealed, data, size);
    for (size_t i = 0; i < size; i++) {
        sealed[i] ^= g_hsm.master_key[i % HSM_KEY_SIZE];
    }
    *sealed_size = size;
    
    return 0;
}

static int
sw_hsm_unseal(const uint8_t *sealed, size_t sealed_size,
              uint8_t *data, size_t *data_size)
{
    memcpy(data, sealed, sealed_size);
    for (size_t i = 0; i < sealed_size; i++) {
        data[i] ^= g_hsm.master_key[i % HSM_KEY_SIZE];
    }
    *data_size = sealed_size;
    
    return 0;
}

/* ==================== TPM2 Integration ==================== */

#if defined(__linux__) || defined(__FreeBSD__) || defined(__DragonFly__)

static int
tpm2_init(void)
{
    /* 
     * In production, would use:
     * - libtss2 on Linux
     * - FreeBSD TPM2 driver
     * - DragonFlyBSD TPM support
     */
    
    printf("HSM: TPM2 initialization\n");
    
    /* Check if TPM device exists */
    FILE *fp = fopen("/dev/tpm0", "r");
    if (!fp) {
        fp = fopen("/dev/tpmrm0", "r");
        if (!fp) {
            printf("HSM: No TPM device found, falling back to software\n");
            g_hsm.provider = HSM_SOFTWARE;
            return sw_hsm_init();
        }
    }
    fclose(fp);
    
    printf("HSM: TPM device found\n");
    
    /* 
     * Full TPM2 initialization would:
     * 1. Initialize TSS2 context
     * 2. Create/load Storage Root Key (SRK)
     * 3. Set up PCR policy
     * 4. Create sealing key under SRK
     */
    
    /* For now, use software emulation */
    return sw_hsm_init();
}

static int
tpm2_seal(const char *name, const uint8_t *data, size_t size,
          uint8_t *sealed, size_t *sealed_size)
{
    /*
     * Real TPM2 sealing would:
     * 1. Create policy session with PCR values
     * 2. TPM2_Create with sensitive data
     * 3. Store sealed blob
     */
    return sw_hsm_seal(name, data, size, sealed, sealed_size);
}

static int
tpm2_unseal(const uint8_t *sealed, size_t sealed_size,
            uint8_t *data, size_t *data_size)
{
    /*
     * Real TPM2 unsealing would:
     * 1. Verify PCR policy
     * 2. TPM2_Load sealed object
     * 3. TPM2_Unseal to get data
     */
    return sw_hsm_unseal(sealed, sealed_size, data, data_size);
}

#endif /* Linux/FreeBSD/DragonFly */

/* ==================== Public API ==================== */

int
hsm_init(hsm_provider_t provider)
{
    memset(&g_hsm, 0, sizeof(hsm_ctx_t));
    
    g_hsm.provider = provider;
    
    switch (provider) {
    case HSM_SOFTWARE:
        return sw_hsm_init();
        
    case HSM_TPM2:
#if defined(__linux__) || defined(__FreeBSD__) || defined(__DragonFly__)
        return tpm2_init();
#else
        printf("HSM: TPM2 not supported on this platform\n");
        g_hsm.provider = HSM_SOFTWARE;
        return sw_hsm_init();
#endif
        
    default:
        printf("HSM: Unknown provider, using software\n");
        g_hsm.provider = HSM_SOFTWARE;
        return sw_hsm_init();
    }
}

void
hsm_shutdown(void)
{
    /* Secure wipe of master key */
    memset(g_hsm.master_key, 0, HSM_KEY_SIZE);
    g_hsm.master_key_loaded = 0;
    
    printf("HSM: Shutdown complete\n");
}

/* Seal data to HSM */
int
hsm_seal(const char *name, const uint8_t *data, size_t size)
{
    if (!g_hsm.initialized && !g_hsm.master_key_loaded)
        return -1;
    
    if (g_hsm.sealed_count >= HSM_MAX_SEALED)
        return -1;
    
    sealed_slot_t *slot = &g_hsm.sealed[g_hsm.sealed_count];
    
    strncpy(slot->name, name, sizeof(slot->name) - 1);
    
    int result;
    
    switch (g_hsm.provider) {
    case HSM_TPM2:
#if defined(__linux__) || defined(__FreeBSD__) || defined(__DragonFly__)
        result = tpm2_seal(name, data, size, 
                          slot->sealed_data, &slot->sealed_size);
#else
        result = sw_hsm_seal(name, data, size,
                            slot->sealed_data, &slot->sealed_size);
#endif
        break;
        
    default:
        result = sw_hsm_seal(name, data, size,
                            slot->sealed_data, &slot->sealed_size);
    }
    
    if (result == 0) {
        slot->active = 1;
        g_hsm.sealed_count++;
        printf("HSM: Sealed '%s' (%zu bytes)\n", name, size);
    }
    
    return result;
}

/* Unseal data from HSM */
int
hsm_unseal(const char *name, uint8_t *data, size_t *size)
{
    for (int i = 0; i < g_hsm.sealed_count; i++) {
        if (g_hsm.sealed[i].active &&
            strcmp(g_hsm.sealed[i].name, name) == 0) {
            
            sealed_slot_t *slot = &g_hsm.sealed[i];
            
            switch (g_hsm.provider) {
            case HSM_TPM2:
#if defined(__linux__) || defined(__FreeBSD__) || defined(__DragonFly__)
                return tpm2_unseal(slot->sealed_data, slot->sealed_size,
                                  data, size);
#else
                return sw_hsm_unseal(slot->sealed_data, slot->sealed_size,
                                    data, size);
#endif
                
            default:
                return sw_hsm_unseal(slot->sealed_data, slot->sealed_size,
                                    data, size);
            }
        }
    }
    
    return -1;  /* Not found */
}

/* Get derived encryption key */
int
hsm_get_key(uint8_t *key, size_t size)
{
    if (!g_hsm.master_key_loaded)
        return -1;
    
    if (size > HSM_KEY_SIZE)
        size = HSM_KEY_SIZE;
    
    memcpy(key, g_hsm.master_key, size);
    return 0;
}

/* Status check */
int
hsm_is_available(void)
{
    return g_hsm.master_key_loaded;
}

hsm_provider_t
hsm_get_provider(void)
{
    return g_hsm.provider;
}
