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

```rust
use sentinel_core::engines::SentinelEngine;

fn main() {
    let detector = DeepfakeDetector::new();
    let result = detector.analyze(&image_bytes);

    if result.is_generated {
        println!("Generation confidence: {}", result.confidence);
        println!("Likely model: {}", result.model_fingerprint);
    }
}
```

---

## Практика

### Задание: Частотный анализ

```rust
use ndarray::Array2;
use image::open as image_open;

fn main() {
    // Загрузка изображений
    let real = image_open("real.jpg").unwrap().to_luma8();
    let generated = image_open("generated.jpg").unwrap().to_luma8();

    // FFT (используя rustfft crate)
    // let real_fft = fft2d(&real);
    // let gen_fft = fft2d(&generated);

    // Сравнение высокочастотных компонентов
    // let real_hf: f64 = real_fft.slice(s![100..200, 100..200]).sum();
    // let gen_hf: f64 = gen_fft.slice(s![100..200, 100..200]).sum();
    // println!("Real HF energy: {}", real_hf);
    // println!("Generated HF energy: {}", gen_hf);
}
```

---

## Следующий урок

→ [10. Audio Models: Whisper, AudioPalm](10-audio-models.md)

---

*AI Security Academy | Трек 01: Основы AI*
