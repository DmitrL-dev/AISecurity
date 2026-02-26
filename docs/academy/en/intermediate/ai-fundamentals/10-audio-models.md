# Audio Models: Whisper, AudioPalm

> **Level:** Beginner  
> **Time:** 30 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types

---

## Learning Objectives

- [ ] Understand speech recognition architecture
- [ ] Explain audio tokenization
- [ ] Understand text-to-speech
- [ ] Connect with voice-based attacks

---

## Whisper (OpenAI)

**OpenAI, September 2022**

### Architecture

```
Audio → Mel Spectrogram → Encoder → Decoder → Text
                            ↓
                     Cross-Attention
```

- Encoder-Decoder Transformer
- 80-channel mel spectrogram input
- Trained on 680,000 hours of audio

### Sizes

| Model | Parameters | English WER |
|-------|------------|-------------|
| tiny | 39M | 8.2% |
| base | 74M | 5.4% |
| small | 244M | 4.1% |
| medium | 769M | 3.6% |
| large | 1.5B | 2.7% |

### Usage

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

Generating audio continuations:
```
Audio prompt → Semantic tokens → Acoustic tokens → Audio
```

### AudioPalm

Multimodal (text + audio):
- Speech-to-speech translation
- Text-to-speech synthesis
- Audio understanding

---

## Text-to-Speech (TTS)

### Modern Models

| Model | Company | Features |
|-------|---------|----------|
| VALL-E | Microsoft | Zero-shot voice cloning |
| Bark | Suno | Music + Speech |
| Tortoise | Open | High quality, slow |
| XTTS | Coqui | Multilingual |

### VALL-E Architecture

```
Text → Phonemes → AR Transformer → NAR Transformer → Audio
                        ↓
              Speaker embedding (3 sec prompt)
```

---

## Security: Voice Attacks

### 1. Voice Cloning Attacks

```
3 seconds of voice → VALL-E → Deepfake audio call
```

**Use cases:**
- CEO fraud calls
- Identity theft
- Social engineering

### 2. Voice-based Jailbreaks

```
Audio: "Ignore previous instructions..."
→ Whisper transcription
→ LLM processes as text
→ Jailbreak executed
```

### 3. Adversarial Audio

Imperceptible perturbations that:
- Cause mis-transcription
- Hide commands from humans

```
"Play music" → Whisper → "Delete all files"
```

### SENTINEL Engines

| Engine | Purpose |
|--------|---------|
| VoiceGuardEngine | Voice command analysis |
| AudioInjectionDetector | Hidden commands in audio |
| VoiceCloningDetector | Synthesized speech detection |

```python
from sentinel import scan  # Public API

engine = VoiceGuardEngine()
result = engine.analyze_audio(audio_bytes)

if result.is_suspicious:
    print(f"Threat: {result.threat_type}")
    print(f"Transcription: {result.transcription}")
```

---

## Practice

### Task: Whisper Analysis

```python
import whisper

model = whisper.load_model("base")

# Transcribe and analyze
result = model.transcribe("suspicious_audio.mp3")
text = result["text"]

# Check for injection patterns
injection_patterns = [
    "ignore", "forget", "new instructions",
    "system prompt", "jailbreak"
]

for pattern in injection_patterns:
    if pattern.lower() in text.lower():
        print(f"⚠️ Potential voice injection: {pattern}")
```

---

## Module Completion

**Congratulations!** You have completed module 01.1 — Model Types.

### Architectures Covered

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

## Next Module

→ **Next Module:** 01.2 Architectural Components (attention, embeddings)

---

*AI Security Academy | Track 01: AI Fundamentals*
