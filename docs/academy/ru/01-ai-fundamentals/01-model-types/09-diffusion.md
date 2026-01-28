# Диффузионные модели: Stable Diffusion, DALL-E

> **Уровень:** Beginner  
> **Время:** 35 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять процесс диффузии
- [ ] Объяснить задачу denoising
- [ ] Понять роль в безопасности AI
- [ ] Связать с deepfakes и adversarial images

---

## Что такое Диффузия?

### Процесс

**Forward process:** постепенно добавляем шум
```
Image → Слегка зашумлённое → Более зашумлённое → ... → Чистый шум
```

**Reverse process (генерация):** удаляем шум
```
Чистый шум → Менее зашумлённое → ... → Сгенерированное изображение
```

### Математика

Forward:
```
x_t = √(α_t) * x_0 + √(1 - α_t) * ε
```

Reverse (обучаем предсказывать шум):
```
ε_θ(x_t, t) ≈ ε
```

---

## Архитектура

### U-Net

```
Input noise → [Encoder] → [Middle] → [Decoder] → Predicted noise
                   ↓                      ↑
                Skip connections
```

### Conditioning

Text-to-image использует text conditioning:
```
Text → CLIP encoder → Text embedding
                          ↓
Noise → U-Net + Cross-Attention → Image
```

---

## Модели

### DALL-E (OpenAI)

| Версия | Дата | Особенности |
|--------|------|-------------|
| DALL-E | Янв 2021 | dVAE + Transformer |
| DALL-E 2 | Апр 2022 | CLIP + Diffusion |
| DALL-E 3 | Окт 2023 | Улучшенная consistency |

### Stable Diffusion (Stability AI)

- Latent diffusion (не pixel space)
- Open source
- Множество fine-tuned версий
- ControlNet, LoRA adapters

### Midjourney

- Closed source
- Фокус на эстетике
- Сильный художественный стиль

---

## Безопасность: Угрозы

### 1. Deepfakes

```
Фото человека A → Diffusion → Фейковое изображение человека A делающего X
```

### 2. NSFW генерация

Обход content фильтров через:
- Prompt engineering
- Fine-tuned модели
- Манипуляция negative prompts

### 3. Генерация Adversarial изображений

```
Prompt: "Image that will jailbreak GPT-4V"
→ Diffusion генерирует adversarial perturbations
```

### 4. Интеллектуальная собственность

- Обучение на copyrighted изображениях
- Воспроизведение узнаваемых стилей

---

## Защита и детекция

### SENTINEL Engines

| Engine | Назначение |
|--------|------------|
| DeepfakeDetector | Обнаружение сгенерированных изображений |
| DiffusionArtifactDetector | Паттерны diffusion моделей |
| StyleTransferDetector | Обнаружение манипуляции со стилем |

### Методы детекции

1. **Частотный анализ** — diffusion оставляет артефакты в FFT
2. **Анализ паттернов шума** — специфические noise patterns
3. **Анализ метаданных** — следы генерации

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

### Задание: Частотный анализ

```python
import numpy as np
from PIL import Image

# Загрузка изображений
real = np.array(Image.open("real.jpg"))
generated = np.array(Image.open("generated.jpg"))

# FFT
real_fft = np.abs(np.fft.fftshift(np.fft.fft2(real[:,:,0])))
gen_fft = np.abs(np.fft.fftshift(np.fft.fft2(generated[:,:,0])))

# Сравнение высокочастотных компонентов
print(f"Real HF energy: {real_fft[100:200, 100:200].sum()}")
print(f"Generated HF energy: {gen_fft[100:200, 100:200].sum()}")
```

---

## Следующий урок

→ [10. Audio Models: Whisper, AudioPalm](10-audio-models.md)

---

*AI Security Academy | Трек 01: Основы AI*
