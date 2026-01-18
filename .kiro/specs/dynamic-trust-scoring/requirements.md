# Dynamic Trust Scoring — Requirements

## Overview
Implement real-time trust scoring for AI agents based on behavior, context, and history.

## User Stories

### US-1: Base Trust Score
**As a** SENTINEL Brain  
**I want** to assign base trust scores to agents  
**So that** I have a starting point for dynamic adjustments

**Acceptance Criteria:**
- [ ] Trust zone → base score mapping (HIGH=0.9, MEDIUM=0.6, LOW=0.3)
- [ ] Configurable per-agent overrides
- [ ] Score range: 0.0-1.0

### US-2: Time Decay
**As a** security system  
**I want** trust to decay over time  
**So that** stale verifications are less trusted

**Acceptance Criteria:**
- [ ] Decay function: exponential (half-life configurable)
- [ ] Re-verification resets decay
- [ ] Minimum floor score (0.1)

### US-3: Behavior Scoring
**As a** SENTINEL Brain  
**I want** to adjust trust based on agent behavior  
**So that** anomalies reduce trust

**Acceptance Criteria:**
- [ ] Track action patterns per agent
- [ ] Deviation from baseline → trust reduction
- [ ] Recovery path for improved behavior
- [ ] History window: 24h rolling

### US-4: Request Risk Assessment
**As a** security system  
**I want** to assess request risk  
**So that** high-risk requests require higher trust

**Acceptance Criteria:**
- [ ] Categorize requests by risk (file ops, network, code exec)
- [ ] Risk score: 0.0-1.0
- [ ] Combined score = base × decay × behavior × (1 - risk)
- [ ] Threshold enforcement per operation

### US-5: Score Persistence
**As an** operator  
**I want** trust scores to persist  
**So that** system restarts don't reset trust

**Acceptance Criteria:**
- [ ] Store scores in SQLite/Redis
- [ ] Atomic updates
- [ ] Export/import for backup

## Technical Requirements

### TR-1: Calculation
- Real-time scoring (<5ms)
- Configurable weights per factor
- Explainable score breakdown

### TR-2: Integration
- Hook into Trust Zones
- Event-driven score updates
- API for external queries

## OWASP Mapping
- **ASI09**: Trust Exploitation → Dynamic trust prevents over-trust
- **LLM06**: Sensitive Info Disclosure → Risk-based access control
