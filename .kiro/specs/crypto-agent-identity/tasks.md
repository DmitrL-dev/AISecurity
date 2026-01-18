# Cryptographic Agent Identity — Tasks

## Implementation Tasks

### Phase 1: Core Crypto
- [ ] Create `src/brain/security/crypto_identity.py`
  - [ ] CryptoIdentityManager class
  - [ ] generate_identity() 
  - [ ] sign_request()
  - [ ] verify_request()
- [ ] Create `src/brain/security/keystore.py`
  - [ ] EncryptedKeyStore class
  - [ ] save() with AES-256-GCM
  - [ ] load() with decryption

### Phase 2: Integration
- [ ] Modify `src/brain/security/trust_zones.py`
  - [ ] Add crypto_manager dependency
  - [ ] Add validate_request() crypto check
  - [ ] Configure per-zone requirements

### Phase 3: Testing
- [ ] Create `tests/test_crypto_identity.py`
  - [ ] test_generate_identity
  - [ ] test_sign_request
  - [ ] test_verify_valid_signature
  - [ ] test_verify_invalid_signature
  - [ ] test_replay_attack_prevention
  - [ ] test_timestamp_expiry
- [ ] Create `tests/test_keystore.py`
  - [ ] test_save_load_roundtrip
  - [ ] test_encrypted_at_rest
