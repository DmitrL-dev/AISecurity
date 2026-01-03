/*
 * SENTINEL IMMUNE — Hive Crypto Module
 * 
 * Cryptographic functions for secure communication.
 * Uses OpenSSL/LibreSSL.
 */

#ifndef IMMUNE_CRYPTO_H
#define IMMUNE_CRYPTO_H

#include <stdint.h>
#include <stdbool.h>

/* Key sizes */
#define AES_KEY_SIZE        32      /* AES-256 */
#define AES_IV_SIZE         12      /* GCM nonce */
#define AES_TAG_SIZE        16      /* GCM tag */
#define RSA_KEY_SIZE        4096
#define SHA256_DIGEST_SIZE  32

/* ==================== Structures ==================== */

typedef struct {
    uint8_t key[AES_KEY_SIZE];
    uint8_t iv[AES_IV_SIZE];
} aes_key_t;

typedef struct {
    void    *private_key;   /* EVP_PKEY */
    void    *public_key;    /* EVP_PKEY */
    uint8_t fingerprint[SHA256_DIGEST_SIZE];
} rsa_keypair_t;

typedef struct {
    void    *cert;          /* X509 */
    char    subject[256];
    char    issuer[256];
    time_t  valid_from;
    time_t  valid_to;
} certificate_t;

/* ==================== Functions ==================== */

/* Initialization */
int crypto_init(void);
void crypto_shutdown(void);

/* Random */
int crypto_random(uint8_t *buffer, size_t length);

/* Hashing */
int crypto_sha256(const uint8_t *data, size_t len,
                  uint8_t *digest);
int crypto_hmac_sha256(const uint8_t *key, size_t key_len,
                       const uint8_t *data, size_t data_len,
                       uint8_t *mac);

/* AES-256-GCM */
int crypto_aes_encrypt(const uint8_t *plaintext, size_t plain_len,
                       const aes_key_t *key,
                       uint8_t *ciphertext, uint8_t *tag);
int crypto_aes_decrypt(const uint8_t *ciphertext, size_t cipher_len,
                       const aes_key_t *key, const uint8_t *tag,
                       uint8_t *plaintext);

/* RSA */
int crypto_rsa_generate(rsa_keypair_t *keypair);
int crypto_rsa_encrypt(const rsa_keypair_t *keypair,
                       const uint8_t *plaintext, size_t plain_len,
                       uint8_t *ciphertext, size_t *cipher_len);
int crypto_rsa_decrypt(const rsa_keypair_t *keypair,
                       const uint8_t *ciphertext, size_t cipher_len,
                       uint8_t *plaintext, size_t *plain_len);
int crypto_rsa_sign(const rsa_keypair_t *keypair,
                    const uint8_t *data, size_t data_len,
                    uint8_t *signature, size_t *sig_len);
int crypto_rsa_verify(const rsa_keypair_t *keypair,
                      const uint8_t *data, size_t data_len,
                      const uint8_t *signature, size_t sig_len);
void crypto_rsa_free(rsa_keypair_t *keypair);

/* Key derivation */
int crypto_pbkdf2(const char *password, size_t pass_len,
                  const uint8_t *salt, size_t salt_len,
                  int iterations,
                  uint8_t *key, size_t key_len);

/* Certificates */
int crypto_cert_generate(rsa_keypair_t *keypair,
                        const char *common_name,
                        int days_valid,
                        certificate_t *cert);
int crypto_cert_verify(const certificate_t *cert,
                       const certificate_t *ca_cert);
void crypto_cert_free(certificate_t *cert);

/* Key export/import */
int crypto_rsa_export_public(const rsa_keypair_t *keypair,
                             uint8_t *buffer, size_t *len);
int crypto_rsa_import_public(rsa_keypair_t *keypair,
                             const uint8_t *buffer, size_t len);

#endif /* IMMUNE_CRYPTO_H */
