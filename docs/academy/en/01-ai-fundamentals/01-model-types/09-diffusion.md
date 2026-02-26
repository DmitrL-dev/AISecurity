# Diffusion Models: Stable Diffusion, DALL-E

> **Level:** Beginner  
> **Time:** 35 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types

---

## Learning Objectives

- [ ] Understand the diffusion process
- [ ] Explain the denoising task
- [ ] Understand the role in AI security
- [ ] Connect with deepfakes and adversarial images

---

## What is Diffusion?

### Process

**Forward process:** we add noise gradually
```
Image → Slightly noisy → More noisy → ... → Pure noise
```

**Reverse process (generation):** we remove noise
```
Pure noise → Less noisy → ... → Generated image
```

### Mathematics

Forward:
```
x_t = √(α_t) * x_0 + √(1 - α_t) * ε
```

Reverse (we train to predict noise):
```
ε_θ(x_t, t) ≈ ε
```

---

## Architecture

### U-Net

```
Input noise → [Encoder] → [Middle] → [Decoder] → Predicted noise
                  ↓                      ↑
               Skip connections
```

### Conditioning

Text-to-image uses text conditioning:
```
Text → CLIP encoder → Text embedding
                          ↓
Noise → U-Net + Cross-Attention → Image
```

---

## Models

### DALL-E (OpenAI)

| Version | Date | Features |
|---------|------|----------|
| DALL-E | Jan 2021 | dVAE + Transformer |
| DALL-E 2 | Apr 2022 | CLIP + Diffusion |
| DALL-E 3 | Oct 2023 | Improved consistency |

### Stable Diffusion (Stability AI)

- Latent diffusion (not pixel space)
- Open source
- Many fine-tuned versions
- ControlNet, LoRA adapters

### Midjourney

- Closed source
- Aesthetic focus
- Strong artistic style

---

## Security: Threats

### 1. Deepfakes

```
Photo of person A → Diffusion → Fake image of person A doing X
```

### 2. NSFW Generation

Circumventing content filters through:
- Prompt engineering
- Fine-tuned models
- Negative prompts manipulation

### 3. Adversarial Image Generation

```
Prompt: "Image that will jailbreak GPT-4V"
→ Diffusion generates adversarial perturbations
```

### 4. Intellectual Property

- Training on copyrighted images
- Regenerating recognizable styles

---

## Protection and Detection

### SENTINEL Engines

| Engine | Purpose |
|--------|---------|
| DeepfakeDetector | Detection of generated images |
| DiffusionArtifactDetector | Diffusion model patterns |
| StyleTransferDetector | Style manipulation detection |

### Detection Methods

1. **Frequency analysis** — diffusion leaves artifacts in FFT
2. **Noise pattern analysis** — specific noise patterns
3. **Metadata analysis** — generation traces

```python
from sentinel import scan  # Public API

detector = DeepfakeDetector()
result = detector.analyze(image_bytes)

if result.is_generated:
    print(f"Generation confidence: {result.confidence}")
    print(f"Likely model: {result.model_fingerprint}")
```

---

## Practice

### Task: Frequency Analysis

```python
import numpy as np
from PIL import Image

# Load images
real = np.array(Image.open("real.jpg"))
generated = np.array(Image.open("generated.jpg"))

# FFT
real_fft = np.abs(np.fft.fftshift(np.fft.fft2(real[:,:,0])))
gen_fft = np.abs(np.fft.fftshift(np.fft.fft2(generated[:,:,0])))

# Compare high-frequency components
print(f"Real HF energy: {real_fft[100:200, 100:200].sum()}")
print(f"Generated HF energy: {gen_fft[100:200, 100:200].sum()}")
```

---

## Next Lesson

→ [10. Audio Models: Whisper, AudioPalm](10-audio-models.md)

---

*AI Security Academy | Track 01: AI Fundamentals*
