# Module 20: Post-Quantum Cryptography (PQC)

## Overview

Post-Quantum Cryptography (PQC) refers to cryptographic algorithms resistant to quantum computer attacks. SENTINEL Shield includes built-in PQC integration for protecting Shield↔Brain communications in the future.

---

## Why PQC Matters

```
┌────────────────────────────────────────────────────────────┐
│            Classical vs Quantum Threats                     │
├─────────────────────────────┬──────────────────────────────┤
│   RSA/ECC Today             │   Quantum Computer           │
│   • Secure                  │   • Shor's Algorithm         │
│   • Widely used             │   • RSA/ECC broken           │
│   • Standardized            │   • "Harvest Now, Decrypt    │
│                             │     Later" attacks           │
└─────────────────────────────┴──────────────────────────────┘
```

**NIST Post-Quantum Standards (2024):**
- **Kyber** → Key Encapsulation (ML-KEM)
- **Dilithium** → Digital Signatures (ML-DSA)

---

## PQC in SENTINEL Shield

### Kyber-1024 (ML-KEM)

**Purpose:** Secure key exchange

**Security Level:** NIST Level 5 (equivalent to AES-256)

```c
// Key sizes
#define KYBER1024_PK_SIZE    1568  // Public key
#define KYBER1024_SK_SIZE    3168  // Secret key
#define KYBER1024_CT_SIZE    1568  // Ciphertext
#define KYBER1024_SS_SIZE    32    // Shared secret
```

**Usage:**
```c
// 1. Generate key pair
kyber1024_keypair(pk, sk);

// 2. Encapsulation (sender)
kyber1024_encapsulate(ct, ss, pk);  // ct = ciphertext, ss = shared secret

// 3. Decapsulation (receiver)
kyber1024_decapsulate(ss, ct, sk);  // ss = same shared secret
```

### Dilithium-5 (ML-DSA)

**Purpose:** Digital signatures

**Security Level:** NIST Level 5

```c
// Key sizes
#define DILITHIUM5_PK_SIZE   2592  // Public key
#define DILITHIUM5_SK_SIZE   4880  // Secret key
#define DILITHIUM5_SIG_SIZE  4627  // Signature
```

**Usage:**
```c
// 1. Generate key pair
dilithium5_keypair(pk, sk);

// 2. Sign
dilithium5_sign(sig, msg, msg_len, sk);

// 3. Verify
int valid = dilithium5_verify(sig, msg, msg_len, pk);
```

---

## PQC API

```c
#include "shield_pqc.h"

// Initialize PQC subsystem
shield_err_t pqc_init(void);

// Get status
pqc_stats_t pqc_get_stats(void);

// Kyber operations
shield_err_t pqc_kyber_keypair(kyber_pk_t *pk, kyber_sk_t *sk);
shield_err_t pqc_kyber_encapsulate(kyber_ct_t *ct, uint8_t ss[32], 
                                    const kyber_pk_t *pk);
shield_err_t pqc_kyber_decapsulate(uint8_t ss[32], const kyber_ct_t *ct,
                                    const kyber_sk_t *sk);

// Dilithium operations
shield_err_t pqc_dilithium_keypair(dilithium_pk_t *pk, dilithium_sk_t *sk);
shield_err_t pqc_dilithium_sign(dilithium_sig_t *sig, const uint8_t *msg,
                                 size_t msg_len, const dilithium_sk_t *sk);
shield_err_t pqc_dilithium_verify(const dilithium_sig_t *sig, 
                                   const uint8_t *msg, size_t msg_len,
                                   const dilithium_pk_t *pk);
```

---

## CLI Commands

```
sentinel# show pqc
PQC (Post-Quantum Cryptography)
===============================
State: ENABLED
Algorithms:
  Key Exchange: Kyber-1024 (NIST Level 5)
  Signatures:   Dilithium-5 (NIST Level 5)

Statistics:
  Keys Generated: 12
  Encapsulations: 45
  Signatures: 23

sentinel(config)# pqc enable
PQC enabled

sentinel# pqc test
Running PQC self-test...
Kyber-1024:
  Keypair generation: OK (2.3ms)
  Encapsulation:      OK (0.4ms)
  Decapsulation:      OK (0.5ms)
Dilithium-5:
  Keypair generation: OK (3.1ms)
  Sign:               OK (1.2ms)
  Verify:             OK (1.0ms)
All tests PASSED
```

---

## Practical Applications

### 1. Shield↔Brain Secure Channel

```
Shield                              Brain
  │                                   │
  │  ───── Kyber Encapsulation ────►  │
  │  ◄──── Shared Secret ──────────   │
  │                                   │
  │  ══════ AES-256-GCM tunnel ═════  │
  │        (key = Kyber SS)           │
```

### 2. Signed Signature Updates

```c
// Brain signs signature update
dilithium5_sign(sig, signature_update, update_len, brain_sk);

// Shield verifies before applying
if (dilithium5_verify(sig, signature_update, update_len, brain_pk)) {
    apply_signature_update(signature_update);
}
```

---

## Integration Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | PQC stubs | ✅ Complete |
| 2 | liboqs integration | ⏳ Planned |
| 3 | Hybrid mode (Classical + PQC) | ⏳ Planned |
| 4 | Full PQC migration | 🔮 Future |

---

## Lab Exercise LAB-200

### Objective
Understand PQC algorithm operation in Shield.

### Task 1: Enable PQC
```bash
sentinel# configure terminal
sentinel(config)# pqc enable
sentinel(config)# end
sentinel# show pqc
```

### Task 2: Self-Test
```bash
sentinel# pqc test
```

### Task 3: Programmatic Integration
```c
#include "shield_pqc.h"

int main() {
    pqc_init();
    
    // Kyber key exchange
    kyber_pk_t pk;
    kyber_sk_t sk;
    pqc_kyber_keypair(&pk, &sk);
    
    kyber_ct_t ct;
    uint8_t ss1[32], ss2[32];
    pqc_kyber_encapsulate(&ct, ss1, &pk);
    pqc_kyber_decapsulate(ss2, &ct, &sk);
    
    // ss1 == ss2 (shared secret)
    assert(memcmp(ss1, ss2, 32) == 0);
    return 0;
}
```

---

## Self-Check Questions

1. Why is classical cryptography vulnerable to quantum computers?
2. What is "Harvest Now, Decrypt Later"?
3. How does Kyber differ from Dilithium?
4. What does "NIST Level 5" mean?
5. Why is Hybrid mode needed?

---

## Next Module

→ [Module 21: Shield State — Global State Manager](MODULE_21_SHIELD_STATE.md)
