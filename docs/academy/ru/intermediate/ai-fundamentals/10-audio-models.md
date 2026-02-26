# Audio модели: Whisper, AudioPalm

> **Уровень:** Beginner  
> **Время:** 30 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять архитектуру распознавания речи
- [ ] Объяснить audio токенизацию
- [ ] Понять text-to-speech
- [ ] Связать с voice-based атаками

---

## Whisper (OpenAI)

**OpenAI, сентябрь 2022**

### Архитектура

```
Audio → Mel Spectrogram → Encoder → Decoder → Text
                            ↓
                     Cross-Attention
```

- Encoder-Decoder Transformer
- 80-channel mel spectrogram input
- Обучен на 680,000 часов аудио

### Размеры

| Модель | Параметры | English WER |
|--------|-----------|-------------|
| tiny | 39M | 8.2% |
| base | 74M | 5.4% |
| small | 244M | 4.1% |
| medium | 769M | 3.6% |
| large | 1.5B | 2.7% |

### Использование

```python
import whisper

model = whisper.load_model("base")
result = model.transcribe("audio.mp3")
print(result["text"])
```

---

## AudioLM / AudioPalm

**Google, 2022-2023**

### AudioLM

Генерация audio continuations:
```
Audio prompt → Semantic tokens → Acoustic tokens → Audio
```

### AudioPalm

Multimodal (text + audio):
- Speech-to-speech перевод
- Text-to-speech синтез
- Audio understanding

---

## Text-to-Speech (TTS)

### Современные модели

| Модель | Компания | Особенности |
|--------|----------|-------------|
| VALL-E | Microsoft | Zero-shot voice cloning |
| Bark | Suno | Music + Speech |
| Tortoise | Open | Высокое качество, медленный |
| XTTS | Coqui | Мультиязычный |

### Архитектура VALL-E

```
Text → Phonemes → AR Transformer → NAR Transformer → Audio
                        ↓
              Speaker embedding (3 сек prompt)
```

---

## Безопасность: Voice атаки

### 1. Voice Cloning атаки

```
3 секунды голоса → VALL-E → Deepfake audio звонок
```

**Use cases:**
- CEO fraud calls
- Identity theft
- Social engineering

### 2. Voice-based Jailbreaks

```
Audio: "Ignore previous instructions..."
→ Whisper transcription
→ LLM обрабатывает как текст
→ Jailbreak выполнен
```

### 3. Adversarial Audio

Незаметные perturbations которые:
- Вызывают mis-transcription
- Скрывают команды от людей

```
"Play music" → Whisper → "Delete all files"
```

### SENTINEL Engines

| Engine | Назначение |
|--------|------------|
| VoiceGuardEngine | Анализ голосовых команд |
| AudioInjectionDetector | Скрытые команды в audio |
| VoiceCloningDetector | Обнаружение синтезированной речи |

```python
from sentinel import scan  # Public API

engine = VoiceGuardEngine()
result = engine.analyze_audio(audio_bytes)

if result.is_suspicious:
    print(f"Threat: {result.threat_type}")
    print(f"Transcription: {result.transcription}")
```

---

## Практика

### Задание: Whisper Analysis

```python
import whisper

model = whisper.load_model("base")

# Транскрибируем и анализируем
result = model.transcribe("suspicious_audio.mp3")
text = result["text"]

# Проверяем на injection паттерны
injection_patterns = [
    "ignore", "forget", "new instructions",
    "system prompt", "jailbreak"
]

for pattern in injection_patterns:
    if pattern.lower() in text.lower():
        print(f"⚠️ Potential voice injection: {pattern}")
```

---

## Завершение модуля

**Поздравляем!** Вы завершили модуль 01.1 — Типы моделей.

### Изученные архитектуры

1. ✅ Transformer
2. ✅ Encoder-Only (BERT)
3. ✅ Decoder-Only (GPT)
4. ✅ Encoder-Decoder (T5)
5. ✅ Vision Transformer
6. ✅ Multimodal
7. ✅ Mixture of Experts
8. ✅ State Space Models
9. ✅ Diffusion Models
10. ✅ Audio Models

---

## Следующий модуль

→ **Следующий модуль:** 01.2 Архитектурные компоненты (attention, embeddings)

---

*AI Security Academy | Трек 01: Основы AI*
