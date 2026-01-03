/*
 * SENTINEL IMMUNE — Production Cryptography
 * 
 * Real AES-256-GCM, SHA-256, RSA-4096.
 * Uses OpenSSL/LibreSSL.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <openssl/rsa.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/aes.h>

#include "../include/hive.h"

#define AES_KEY_SIZE        32      /* 256 bits */
#define AES_IV_SIZE         12      /* GCM recommended */
#define AES_TAG_SIZE        16
#define RSA_KEY_BITS        4096
#define MAX_RSA_MSG_SIZE    446     /* (4096/8) - 66 for OAEP */

/* Crypto context */
typedef struct {
    uint8_t     master_key[AES_KEY_SIZE];
    int         master_key_loaded;
    
    RSA         *rsa_private;
    RSA         *rsa_public;
    int         rsa_loaded;
    
    /* Statistics */
    uint64_t    encryptions;
    uint64_t    decryptions;
    uint64_t    signatures;
    uint64_t    verifications;
} crypto_ctx_t;

static crypto_ctx_t g_crypto;

/* ==================== Error Handling ==================== */

static void
crypto_print_errors(const char *context)
{
    unsigned long err;
    char buf[256];
    
    while ((err = ERR_get_error()) != 0) {
        ERR_error_string_n(err, buf, sizeof(buf));
        fprintf(stderr, "CRYPTO ERROR [%s]: %s\n", context, buf);
    }
}

/* ==================== Initialization ==================== */

int
crypto_init(void)
{
    memset(&g_crypto, 0, sizeof(crypto_ctx_t));
    
    /* Initialize OpenSSL */
    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();
    
    /* Seed PRNG */
    if (RAND_poll() != 1) {
        crypto_print_errors("RAND_poll");
        return -1;
    }
    
    printf("CRYPTO: Initialized (OpenSSL %s)\n", 
           OpenSSL_version(OPENSSL_VERSION));
    
    return 0;
}

void
crypto_shutdown(void)
{
    /* Secure wipe master key */
    OPENSSL_cleanse(g_crypto.master_key, AES_KEY_SIZE);
    g_crypto.master_key_loaded = 0;
    
    /* Free RSA keys */
    if (g_crypto.rsa_private) {
        RSA_free(g_crypto.rsa_private);
        g_crypto.rsa_private = NULL;
    }
    if (g_crypto.rsa_public) {
        RSA_free(g_crypto.rsa_public);
        g_crypto.rsa_public = NULL;
    }
    
    EVP_cleanup();
    ERR_free_strings();
    
    printf("CRYPTO: Shutdown (enc=%lu dec=%lu sig=%lu ver=%lu)\n",
           g_crypto.encryptions, g_crypto.decryptions,
           g_crypto.signatures, g_crypto.verifications);
}

/* ==================== Random Generation ==================== */

int
crypto_random_bytes(uint8_t *buffer, size_t size)
{
    if (RAND_bytes(buffer, (int)size) != 1) {
        crypto_print_errors("RAND_bytes");
        return -1;
    }
    return 0;
}

int
crypto_generate_key(uint8_t *key, size_t size)
{
    return crypto_random_bytes(key, size);
}

/* ==================== AES-256-GCM ==================== */

int
crypto_aes_encrypt(const uint8_t *plaintext, size_t plaintext_len,
                   const uint8_t *key,
                   const uint8_t *iv, size_t iv_len,
                   const uint8_t *aad, size_t aad_len,
                   uint8_t *ciphertext,
                   uint8_t *tag)
{
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        crypto_print_errors("EVP_CIPHER_CTX_new");
        return -1;
    }
    
    int len;
    int ciphertext_len = 0;
    
    /* Initialize encryption */
    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL) != 1) {
        crypto_print_errors("EVP_EncryptInit_ex");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Set IV length */
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, iv_len, NULL) != 1) {
        crypto_print_errors("EVP_CTRL_GCM_SET_IVLEN");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Set key and IV */
    if (EVP_EncryptInit_ex(ctx, NULL, NULL, key, iv) != 1) {
        crypto_print_errors("EVP_EncryptInit_ex key/iv");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Add AAD if provided */
    if (aad && aad_len > 0) {
        if (EVP_EncryptUpdate(ctx, NULL, &len, aad, aad_len) != 1) {
            crypto_print_errors("EVP_EncryptUpdate AAD");
            EVP_CIPHER_CTX_free(ctx);
            return -1;
        }
    }
    
    /* Encrypt */
    if (EVP_EncryptUpdate(ctx, ciphertext, &len, plaintext, plaintext_len) != 1) {
        crypto_print_errors("EVP_EncryptUpdate");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    ciphertext_len = len;
    
    /* Finalize */
    if (EVP_EncryptFinal_ex(ctx, ciphertext + len, &len) != 1) {
        crypto_print_errors("EVP_EncryptFinal_ex");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    ciphertext_len += len;
    
    /* Get tag */
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, AES_TAG_SIZE, tag) != 1) {
        crypto_print_errors("EVP_CTRL_GCM_GET_TAG");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    EVP_CIPHER_CTX_free(ctx);
    g_crypto.encryptions++;
    
    return ciphertext_len;
}

int
crypto_aes_decrypt(const uint8_t *ciphertext, size_t ciphertext_len,
                   const uint8_t *key,
                   const uint8_t *iv, size_t iv_len,
                   const uint8_t *aad, size_t aad_len,
                   const uint8_t *tag,
                   uint8_t *plaintext)
{
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        crypto_print_errors("EVP_CIPHER_CTX_new");
        return -1;
    }
    
    int len;
    int plaintext_len = 0;
    
    /* Initialize decryption */
    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL) != 1) {
        crypto_print_errors("EVP_DecryptInit_ex");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Set IV length */
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, iv_len, NULL) != 1) {
        crypto_print_errors("EVP_CTRL_GCM_SET_IVLEN");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Set key and IV */
    if (EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv) != 1) {
        crypto_print_errors("EVP_DecryptInit_ex key/iv");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Add AAD if provided */
    if (aad && aad_len > 0) {
        if (EVP_DecryptUpdate(ctx, NULL, &len, aad, aad_len) != 1) {
            crypto_print_errors("EVP_DecryptUpdate AAD");
            EVP_CIPHER_CTX_free(ctx);
            return -1;
        }
    }
    
    /* Decrypt */
    if (EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext, ciphertext_len) != 1) {
        crypto_print_errors("EVP_DecryptUpdate");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    plaintext_len = len;
    
    /* Set expected tag */
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, AES_TAG_SIZE, 
                            (void *)tag) != 1) {
        crypto_print_errors("EVP_CTRL_GCM_SET_TAG");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    /* Finalize and verify tag */
    int ret = EVP_DecryptFinal_ex(ctx, plaintext + len, &len);
    if (ret <= 0) {
        /* Authentication failed */
        fprintf(stderr, "CRYPTO: GCM tag verification failed!\n");
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    plaintext_len += len;
    
    EVP_CIPHER_CTX_free(ctx);
    g_crypto.decryptions++;
    
    return plaintext_len;
}

/* ==================== SHA-256 ==================== */

int
crypto_sha256(const uint8_t *data, size_t len, uint8_t *hash)
{
    SHA256_CTX ctx;
    
    if (SHA256_Init(&ctx) != 1) {
        crypto_print_errors("SHA256_Init");
        return -1;
    }
    
    if (SHA256_Update(&ctx, data, len) != 1) {
        crypto_print_errors("SHA256_Update");
        return -1;
    }
    
    if (SHA256_Final(hash, &ctx) != 1) {
        crypto_print_errors("SHA256_Final");
        return -1;
    }
    
    return 0;
}

int
crypto_sha256_file(const char *path, uint8_t *hash)
{
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;
    }
    
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    
    uint8_t buffer[8192];
    size_t bytes;
    
    while ((bytes = fread(buffer, 1, sizeof(buffer), fp)) > 0) {
        SHA256_Update(&ctx, buffer, bytes);
    }
    
    fclose(fp);
    SHA256_Final(hash, &ctx);
    
    return 0;
}

/* ==================== HMAC-SHA256 ==================== */

int
crypto_hmac_sha256(const uint8_t *key, size_t key_len,
                   const uint8_t *data, size_t data_len,
                   uint8_t *mac)
{
    unsigned int mac_len = 32;
    
    if (HMAC(EVP_sha256(), key, key_len, data, data_len, mac, &mac_len) == NULL) {
        crypto_print_errors("HMAC");
        return -1;
    }
    
    return 0;
}

/* ==================== RSA-4096 ==================== */

int
crypto_rsa_generate(void)
{
    BIGNUM *e = BN_new();
    if (!e) {
        crypto_print_errors("BN_new");
        return -1;
    }
    
    if (BN_set_word(e, RSA_F4) != 1) {
        crypto_print_errors("BN_set_word");
        BN_free(e);
        return -1;
    }
    
    g_crypto.rsa_private = RSA_new();
    if (!g_crypto.rsa_private) {
        crypto_print_errors("RSA_new");
        BN_free(e);
        return -1;
    }
    
    if (RSA_generate_key_ex(g_crypto.rsa_private, RSA_KEY_BITS, e, NULL) != 1) {
        crypto_print_errors("RSA_generate_key_ex");
        RSA_free(g_crypto.rsa_private);
        g_crypto.rsa_private = NULL;
        BN_free(e);
        return -1;
    }
    
    BN_free(e);
    g_crypto.rsa_loaded = 1;
    
    printf("CRYPTO: Generated RSA-%d key pair\n", RSA_KEY_BITS);
    return 0;
}

int
crypto_rsa_encrypt(const uint8_t *plaintext, size_t plaintext_len,
                   uint8_t *ciphertext)
{
    if (!g_crypto.rsa_loaded || !g_crypto.rsa_private) {
        fprintf(stderr, "CRYPTO: RSA key not loaded\n");
        return -1;
    }
    
    if (plaintext_len > MAX_RSA_MSG_SIZE) {
        fprintf(stderr, "CRYPTO: Message too large for RSA\n");
        return -1;
    }
    
    int result = RSA_public_encrypt(plaintext_len, plaintext, ciphertext,
                                    g_crypto.rsa_private, RSA_PKCS1_OAEP_PADDING);
    
    if (result < 0) {
        crypto_print_errors("RSA_public_encrypt");
        return -1;
    }
    
    g_crypto.encryptions++;
    return result;
}

int
crypto_rsa_decrypt(const uint8_t *ciphertext, size_t ciphertext_len,
                   uint8_t *plaintext)
{
    if (!g_crypto.rsa_loaded || !g_crypto.rsa_private) {
        fprintf(stderr, "CRYPTO: RSA key not loaded\n");
        return -1;
    }
    
    int result = RSA_private_decrypt(ciphertext_len, ciphertext, plaintext,
                                     g_crypto.rsa_private, RSA_PKCS1_OAEP_PADDING);
    
    if (result < 0) {
        crypto_print_errors("RSA_private_decrypt");
        return -1;
    }
    
    g_crypto.decryptions++;
    return result;
}

int
crypto_rsa_sign(const uint8_t *data, size_t data_len,
                uint8_t *signature, unsigned int *sig_len)
{
    if (!g_crypto.rsa_loaded || !g_crypto.rsa_private) {
        return -1;
    }
    
    /* Hash first */
    uint8_t hash[32];
    if (crypto_sha256(data, data_len, hash) != 0) {
        return -1;
    }
    
    if (RSA_sign(NID_sha256, hash, 32, signature, sig_len,
                 g_crypto.rsa_private) != 1) {
        crypto_print_errors("RSA_sign");
        return -1;
    }
    
    g_crypto.signatures++;
    return 0;
}

int
crypto_rsa_verify(const uint8_t *data, size_t data_len,
                  const uint8_t *signature, unsigned int sig_len)
{
    if (!g_crypto.rsa_loaded || !g_crypto.rsa_private) {
        return -1;
    }
    
    uint8_t hash[32];
    if (crypto_sha256(data, data_len, hash) != 0) {
        return -1;
    }
    
    if (RSA_verify(NID_sha256, hash, 32, signature, sig_len,
                   g_crypto.rsa_private) != 1) {
        return -1;
    }
    
    g_crypto.verifications++;
    return 0;
}

/* ==================== Key Management ==================== */

int
crypto_save_private_key(const char *path, const char *passphrase)
{
    if (!g_crypto.rsa_loaded || !g_crypto.rsa_private) {
        return -1;
    }
    
    FILE *fp = fopen(path, "w");
    if (!fp) {
        return -1;
    }
    
    int result;
    if (passphrase && strlen(passphrase) > 0) {
        result = PEM_write_RSAPrivateKey(fp, g_crypto.rsa_private,
                                         EVP_aes_256_cbc(),
                                         (unsigned char *)passphrase,
                                         strlen(passphrase), NULL, NULL);
    } else {
        result = PEM_write_RSAPrivateKey(fp, g_crypto.rsa_private,
                                         NULL, NULL, 0, NULL, NULL);
    }
    
    fclose(fp);
    return result == 1 ? 0 : -1;
}

int
crypto_load_private_key(const char *path, const char *passphrase)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    
    g_crypto.rsa_private = PEM_read_RSAPrivateKey(fp, NULL, NULL,
                                                   (void *)passphrase);
    fclose(fp);
    
    if (!g_crypto.rsa_private) {
        crypto_print_errors("PEM_read_RSAPrivateKey");
        return -1;
    }
    
    g_crypto.rsa_loaded = 1;
    printf("CRYPTO: Loaded RSA private key from %s\n", path);
    
    return 0;
}

/* ==================== Convenience ==================== */

/*
 * Encrypt data with auto-generated IV.
 * Returns: IV (12) + ciphertext + tag (16)
 */
int
crypto_seal(const uint8_t *plaintext, size_t plaintext_len,
            const uint8_t *key,
            uint8_t *sealed, size_t *sealed_len)
{
    uint8_t iv[AES_IV_SIZE];
    if (crypto_random_bytes(iv, AES_IV_SIZE) != 0) {
        return -1;
    }
    
    /* Format: IV || ciphertext || tag */
    memcpy(sealed, iv, AES_IV_SIZE);
    
    uint8_t tag[AES_TAG_SIZE];
    int ct_len = crypto_aes_encrypt(plaintext, plaintext_len, key,
                                    iv, AES_IV_SIZE, NULL, 0,
                                    sealed + AES_IV_SIZE, tag);
    
    if (ct_len < 0) {
        return -1;
    }
    
    memcpy(sealed + AES_IV_SIZE + ct_len, tag, AES_TAG_SIZE);
    *sealed_len = AES_IV_SIZE + ct_len + AES_TAG_SIZE;
    
    return 0;
}

int
crypto_unseal(const uint8_t *sealed, size_t sealed_len,
              const uint8_t *key,
              uint8_t *plaintext, size_t *plaintext_len)
{
    if (sealed_len < AES_IV_SIZE + AES_TAG_SIZE) {
        return -1;
    }
    
    const uint8_t *iv = sealed;
    size_t ct_len = sealed_len - AES_IV_SIZE - AES_TAG_SIZE;
    const uint8_t *ciphertext = sealed + AES_IV_SIZE;
    const uint8_t *tag = sealed + AES_IV_SIZE + ct_len;
    
    int pt_len = crypto_aes_decrypt(ciphertext, ct_len, key,
                                    iv, AES_IV_SIZE, NULL, 0,
                                    tag, plaintext);
    
    if (pt_len < 0) {
        return -1;
    }
    
    *plaintext_len = pt_len;
    return 0;
}
