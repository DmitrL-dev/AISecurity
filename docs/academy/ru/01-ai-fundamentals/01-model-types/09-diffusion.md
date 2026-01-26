# Diffusion Models: Stable Diffusion, DALL-E

> **Уровень:** Начинающий  
> **Время:** 35 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять процесс diffusion
- [ ] Объяснить задачу denoising
- [ ] Понять роль в AI security
- [ ] Связать с deepfakes и adversarial images

---

## Что такое Diffusion?

### Процесс

**Forward process:** постепенно добавляем шум
```
Image > Slightly noisy > More noisy > ... > Pure noise
```

**Reverse process (генерация):** убираем шум
```
Pure noise > Less noisy > ... > Generated image
```

### Математика

Forward:
```
x_t = v(?_t) * x_0 + v(1 - ?_t) * ?
```

Reverse (обучаем предсказывать шум):
```
?_?(x_t, t) ? ?
```

---

## Архитектура

### U-Net

```
Input noise > [Encoder] > [Middle] > [Decoder] > Predicted noise
                  v                      ^
               Skip connections
```

### Conditioning

Text-to-image использует text conditioning:
```
Text > CLIP encoder > Text embedding
                          v
Noise > U-Net + Cross-Attention > Image
```

---

## Модели

### DALL-E (OpenAI)

| Версия | Дата | Особенности |
|--------|------|-------------|
| DALL-E | Jan 2021 | dVAE + Transformer |
| DALL-E 2 | Apr 2022 | CLIP + Diffusion |
| DALL-E 3 | Oct 2023 | Improved consistency |

### Stable Diffusion (Stability AI)

- Latent diffusion (не pixel space)
- Open source
- Много fine-tuned версий
- ControlNet, LoRA adapters

### Midjourney

- Closed source
- Фокус на эстетике
- Сильный художественный стиль

---

## Security: Угрозы

### 1. Deepfakes

```
Photo of person A > Diffusion > Fake image of person A doing X
```

### 2. NSFW Generation

Обход content filters через:
- Prompt engineering
- Fine-tuned модели
- Negative prompts manipulation

### 3. Adversarial Image Generation

```
Prompt: "Image that will jailbreak GPT-4V"
> Diffusion генерирует adversarial perturbations
```

### 4. Intellectual Property

- Обучение на copyrighted images
- Регенерация узнаваемых стилей

---

## Protection и Detection

### SENTINEL Engines

| Engine | Назначение |
|--------|------------|
| DeepfakeDetector | Детекция сгенерированных изображений |
| DiffusionArtifactDetector | Паттерны diffusion модели |
| StyleTransferDetector | Детекция style manipulation |

### Методы детекции

1. **Frequency analysis** — diffusion оставляет артефакты в FFT
2. **Noise pattern analysis** — специфичные паттерны шума
3. **Metadata analysis** — следы генерации

```python
from sentinel import scan  # Public API

detector = DeepfakeDetector()
result = detector.analyze(image_bytes)

if result.is_generated:
    print(f"Generation confidence: {result.confidence}")
    print(f"Likely model: {result.model_fingerprint}")
```

---

## Практика

### Задание: Frequency Analysis

```python
import numpy as np
from PIL import Image

# Загрузка изображений
real = np.array(Image.open("real.jpg"))
generated = np.array(Image.open("generated.jpg"))

# FFT
real_fft = np.abs(np.fft.fftshift(np.fft.fft2(real[:,:,0])))
gen_fft = np.abs(np.fft.fftshift(np.fft.fft2(generated[:,:,0])))

# Сравнение high-frequency компонент
print(f"Real HF energy: {real_fft[100:200, 100:200].sum()}")
print(f"Generated HF energy: {gen_fft[100:200, 100:200].sum()}")
```

---

## Следующий урок

> [10. Audio Models: Whisper, AudioPalm](10-audio-models.md)

---

*AI Security Academy | Track 01: AI Fundamentals*
