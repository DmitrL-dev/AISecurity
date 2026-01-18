# Cryptographic Agent Identity — Requirements

## Overview
Implement Ed25519-based cryptographic identity for AI agents to prevent impersonation, MITM, and replay attacks.

## User Stories

### US-1: Agent Key Generation
**As a** system administrator  
**I want** to generate Ed25519 keypairs for agents  
**So that** each agent has a unique cryptographic identity

**Acceptance Criteria:**
- [ ] Generate Ed25519 private/public keypair
- [ ] Store private key securely (encrypted at rest)
- [ ] Export public key for verification
- [ ] Rotate keys without service interruption

### US-2: Request Signing
**As an** AI agent  
**I want** to sign my requests cryptographically  
**So that** receivers can verify my identity

**Acceptance Criteria:**
- [ ] Sign request payload with Ed25519 private key
- [ ] Include timestamp to prevent replay attacks
- [ ] Include nonce for uniqueness
- [ ] Signature verifiable by receiver

### US-3: Response Verification
**As a** receiving system  
**I want** to verify agent signatures  
**So that** I can trust the request origin

**Acceptance Criteria:**
- [ ] Verify Ed25519 signature against public key
- [ ] Reject expired timestamps (>5 min)
- [ ] Reject duplicate nonces
- [ ] Log verification failures

### US-4: Trust Zone Integration
**As a** SENTINEL Brain  
**I want** to enforce crypto identity in Trust Zones  
**So that** agents are authenticated before operations

**Acceptance Criteria:**
- [ ] HIGH trust zone requires valid signature
- [ ] MEDIUM trust zone can bypass for internal calls
- [ ] LOW trust zone always requires signature
- [ ] Failed verification → block + alert

## Technical Requirements

### TR-1: Cryptography
- Ed25519 (RFC 8032)
- PyNaCl or cryptography library
- Key derivation from master secret

### TR-2: Performance
- Signature generation: <1ms
- Verification: <1ms
- No external service dependency

### TR-3: Security
- Private keys never in logs
- Keys encrypted at rest (AES-256-GCM)
- HSM support (optional, v2)

## OWASP Mapping
- **ASI02**: Inadequate Sandboxing → Signature prevents agent escape
- **ASI03**: Identity/Privilege Abuse → Crypto identity prevents impersonation
- **ASI09**: Trust Exploitation → Verified identity in trust chain

## Out of Scope
- Post-quantum crypto (future version)
- Hardware security modules (v2)
- Multi-party signatures (v2)
