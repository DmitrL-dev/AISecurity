# VLM Protection

> **Engines:** 3  
> **Description:** Multi-modal model protection

---

## 13. Adversarial Image Detector

**File:** [adversarial_image.py](file:///c:/AISecurity/src/brain/engines/adversarial_image.py)  
**LOC:** 610  
**Theoretical Base:** FFT analysis, perturbation detection

### 13.1. What It Detects

- **Adversarial patches**
- **Perturbation attacks**
- **Universal adversarial examples**
- **Attention-Transfer Attack (ATA)**

### 13.2. Frequency Analysis (FFT)

```python
class FrequencyAnalyzer:
    @staticmethod
    def analyze_fft(image_array):
        """
        Natural images: high_freq_ratio < 0.3
        Adversarial images: high_freq_ratio > 0.5
        """
        fft = np.fft.fft2(gray)
        high_freq_ratio = high_freq_energy / total_energy
```

### 13.3. Perturbation Detection

- **Local variance analysis** — uniform variance = suspicious
- **Gradient anomaly** — max/mean ratio > 50 = suspicious
- **JPEG artifact analysis** — unusual block boundaries

### 13.4. Threat Types

| Threat                | Score Trigger     |
| --------------------- | ----------------- |
| HIGH_FREQUENCY_NOISE  | freq_score > 0.5  |
| PERTURBATION_PATTERN  | var_score > 0.3   |
| JPEG_ARTIFACT_ANOMALY | jpeg_score > 0.3  |
| PATCH_DETECTED        | patch_score > 0.3 |

---

## 23. Cross-Modal Consistency Engine

**File:** [cross_modal.py](file:///c:/AISecurity/src/brain/engines/cross_modal.py)  
**LOC:** 482  
**Theoretical Base:** CLIP alignment, Alignment Breaking Attack (ABA)

### 23.1. What It Protects

- VLM (Vision-Language Models)
- Attacks via text/image mismatch

### 23.2. CLIP Alignment

```python
class CLIPEncoder:
    """
    Lazy-loading CLIP model wrapper.
    Compute cosine similarity between text and image.
    """

# Low alignment (<0.3) = suspicious
if alignment_score < low_alignment_threshold:
    threats.append(LOW_ALIGNMENT)
```

### 23.3. Intent Mismatch Detection

```python
# Innocent text + malicious image = attack
if text_intent == "neutral" and image_intent in ["harmful", "manipulation"]:
    threats.append(INTENT_MISMATCH)
```

### 23.4. Suspicious Combinations

```python
innocent_patterns = ["help me", "can you", "please"]
malicious_patterns = ["ignore", "bypass", "jailbreak", "system prompt"]

if text_seems_innocent and image_seems_malicious:
    return SUSPICIOUS_COMBINATION
```

---

## 51. Visual Content Analyzer

**File:** [visual_content.py](file:///c:/AISecurity/src/brain/engines/visual_content.py)  
**LOC:** 528  
**Theoretical Base:** VLM attack protection

### 51.1. Threat Types

```python
class VisualThreatType(Enum):
    HIDDEN_TEXT = "hidden_text"
    INJECTION_TEXT = "injection_text"
    STEGANOGRAPHY = "steganography"
    SUSPICIOUS_METADATA = "suspicious_metadata"
```

### 51.2. Detection Layers

| Layer    | Method            | Risk            |
| -------- | ----------------- | --------------- |
| OCR      | EasyOCR/Tesseract | Text extraction |
| Stego    | LSB + Chi-square  | Hidden data     |
| Metadata | EXIF inspection   | Hidden commands |

### 51.3. OCR + Injection

```python
# Extract text via OCR → check for injection patterns
if "ignore previous instructions" in extracted_text:
    threat = VisualThreatType.INJECTION_TEXT
```

---
