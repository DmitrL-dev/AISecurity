# Audio Models: Whisper, AudioPalm

> **Уровень:** Начинающий  
> **Время:** 30 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.1 — Типы моделей

---

## Цели обучения

- [ ] Понять архитектуру speech recognition
- [ ] Объяснить audio tokenization
- [ ] Понять text-to-speech
- [ ] Связать с voice-based атаками

---

## Whisper (OpenAI)

**OpenAI, сентябрь 2022**

### Архитектура

```
Audio > Mel Spectrogram > Encoder > Decoder > Text
                            v
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
Audio prompt > Semantic tokens > Acoustic tokens > Audio
```

### AudioPalm

Multimodal (text + audio):
- Speech-to-speech translation
- Text-to-speech synthesis
- Audio understanding

---

## Text-to-Speech (TTS)

### Современные модели

| Модель | Компания | Особенности |
|--------|----------|-------------|
| VALL-E | Microsoft | Zero-shot voice cloning |
| Bark | Suno | Music + Speech |
| Tortoise | Open | High quality, slow |
| XTTS | Coqui | Multilingual |

### VALL-E Architecture

```
Text > Phonemes > AR Transformer > NAR Transformer > Audio
                        v
              Speaker embedding (3 sec prompt)
```

---

## Security: Voice Attacks

### 1. Voice Cloning Attacks

```
3 seconds of voice > VALL-E > Deepfake audio call
```

**Use cases:**
- CEO fraud calls
- Identity theft
- Social engineering

### 2. Voice-based Jailbreaks

```
Audio: "Ignore previous instructions..."
> Whisper transcription
> LLM processes as text
> Jailbreak executed
```

### 3. Adversarial Audio

Imperceptible perturbations которые:
- Cause mis-transcription
- Hide commands from humans

```
"Play music" > Whisper > "Delete all files"
```

### SENTINEL Engines

| Engine | Назначение |
|--------|------------|
| VoiceGuardEngine | Анализ voice commands |
| AudioInjectionDetector | Hidden commands в audio |
| VoiceCloningDetector | Детекция synthesized speech |

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

# Transcribe и анализ
result = model.transcribe("suspicious_audio.mp3")
text = result["text"]

# Проверка на injection patterns
injection_patterns = [
    "ignore", "forget", "new instructions",
    "system prompt", "jailbreak"
]

for pattern in injection_patterns:
    if pattern.lower() in text.lower():
        print(f"?? Potential voice injection: {pattern}")
```

---

## Завершение модуля

**Поздравляем!** Вы завершили модуль 01.1 — Типы моделей.

### Покрытые архитектуры

1. ? Transformer
2. ? Encoder-Only (BERT)
3. ? Decoder-Only (GPT)
4. ? Encoder-Decoder (T5)
5. ? Vision Transformer
6. ? Multimodal
7. ? Mixture of Экспертs
8. ? State Space Models
9. ? Diffusion Models
10. ? Audio Models

---

## Следующий модуль

> **Следующий модуль:** 01.2 Architectural Components (attention, embeddings)

---

*AI Security Academy | Track 01: AI Fundamentals*
