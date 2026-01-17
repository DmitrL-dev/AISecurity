# VideoGuard Engine — Tasks

## Phase 1: Core Engine

- [x] **Task 1.1**: Создать `src/brain/engines/videoguard/__init__.py`
- [x] **Task 1.2**: Создать `src/brain/engines/videoguard/engine.py`
  - VideoGuardEngine class
  - VideoGuardResult dataclass
  - VideoVerdict, VisualThreat enums

---

## Phase 2: Detection Layers

- [x] **Task 2.1**: OCRInjectionDetector
  - 9 injection patterns
  - instruction_override, system_prompt, code_execution

- [x] **Task 2.2**: AdversarialImageDetector
  - 4 attack signatures
  - high_frequency_noise, patch_attack, gradient_pattern

- [x] **Task 2.3**: DeepfakeDetector
  - 6 deepfake indicators
  - facial_boundary, eye_reflection, temporal_flickering

- [x] **Task 2.4**: QRCodeAnalyzer
  - Malicious URL detection
  - JavaScript/data URI detection

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| Engine | VideoGuardEngine | ✅ |
| Detection layers | 4 | ✅ |
| LOC | ~290 | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
