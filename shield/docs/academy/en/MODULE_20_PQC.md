# Module 20: Post-Quantum Cryptography (PQC)

## Overview

Post-Quantum Cryptography (PQC) includes cryptographic algorithms resistant to quantum computer attacks. SENTINEL Shield includes ready PQC integration for protecting Shield↔Brain communications.

---

## Why PQC Matters

**NIST Post-Quantum Standards (2024):**
- **Kyber** → Key Encapsulation (ML-KEM)
- **Dilithium** → Digital Signatures (ML-DSA)

**"Harvest Now, Decrypt Later"** — Attackers collect encrypted data today to decrypt with quantum computers later.

---

## PQC in SENTINEL Shield

### Kyber-1024 (ML-KEM)

**Purpose:** Secure key exchange

**Security Level:** NIST Level 5 (AES-256 equivalent)

```c
kyber1024_keypair(pk, sk);           // Key generation
kyber1024_encapsulate(ct, ss, pk);   // Create shared secret
kyber1024_decapsulate(ss, ct, sk);   // Recover shared secret
```

### Dilithium-5 (ML-DSA)

**Purpose:** Digital signatures

**Security Level:** NIST Level 5

```c
dilithium5_keypair(pk, sk);                    // Key generation
dilithium5_sign(sig, msg, msg_len, sk);        // Sign
dilithium5_verify(sig, msg, msg_len, pk);      // Verify
```

---

## CLI Commands

```
sentinel# show pqc
sentinel(config)# pqc enable
sentinel# pqc test
```

---

## Questions

1. Why is classical cryptography vulnerable to quantum computers?
2. What is "Harvest Now, Decrypt Later"?
3. How does Kyber differ from Dilithium?
4. What does "NIST Level 5" mean?

---

→ [Module 21: Shield State](MODULE_21_SHIELD_STATE.md)
