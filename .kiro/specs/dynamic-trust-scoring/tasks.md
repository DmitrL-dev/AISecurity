# Dynamic Trust Scoring — Tasks

## Implementation Tasks

### Phase 1: Core Engine
- [ ] Create `src/brain/security/trust_score.py`
  - [ ] TrustScoreEngine class
  - [ ] calculate() main method
  - [ ] _calculate_decay()
  - [ ] _calculate_behavior_score()
  - [ ] _assess_request_risk()

### Phase 2: History Store
- [ ] Create `src/brain/security/history_store.py`
  - [ ] HistoryStore class
  - [ ] SQLite schema
  - [ ] record_action()
  - [ ] get_actions()
  - [ ] get_last_verification()

### Phase 3: Integration
- [ ] Modify `src/brain/security/trust_zones.py`
  - [ ] Add TrustScoreEngine dependency
  - [ ] Use dynamic score for decisions

### Phase 4: Testing
- [ ] Create `tests/test_trust_score.py`
  - [ ] test_base_score_by_zone
  - [ ] test_time_decay
  - [ ] test_behavior_score
  - [ ] test_request_risk
  - [ ] test_combined_score
