# Fine-tuning и RLHF

> **Уровень:** Beginner  
> **Время:** 50 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.2 — Training Lifecycle  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить процесс fine-tuning для различных задач
- [ ] Понять Instruction Tuning и его роль в современных LLM
- [ ] Описать RLHF (Reinforcement Learning from Human Feedback)
- [ ] Понять атаки на reward models и RLHF pipeline

---

## 1. Fine-tuning: Адаптация к задачам

### 1.1 Типы Fine-tuning

```
Типы Fine-tuning:
├── Task-specific (классификация, NER, QA)
├── Instruction Tuning (следование инструкциям)
├── Preference Tuning (RLHF, DPO)
└── Domain Adaptation (медицина, право)
```

### 1.2 Task-Specific Fine-tuning

```python
from transformers import BertForSequenceClassification, Trainer

# Sentiment Analysis
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=3  # positive, negative, neutral
)

# NER
from transformers import BertForTokenClassification
model = BertForTokenClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=9  # B-PER, I-PER, B-ORG, etc.
)

# Question Answering
from transformers import BertForQuestionAnswering
model = BertForQuestionAnswering.from_pretrained('bert-base-uncased')
```

---

## 2. Instruction Tuning

### 2.1 Что такое Instruction Tuning?

**Проблема:** Pre-trained LLM продолжают текст, но не следуют инструкциям.

```
Pre-trained GPT:
User: "Translate to French: Hello"
Model: "Translate to French: Hello, how are you? This is a common phrase..."
       (продолжает текст, не переводит!)

Instruction-tuned GPT:
User: "Translate to French: Hello"
Model: "Bonjour"
       (следует инструкции!)
```

### 2.2 Формат Instruction датасета

```python
# Формат instruction датасета
instruction_example = {
    "instruction": "Translate the following text to French",
    "input": "Hello, how are you?",
    "output": "Bonjour, comment allez-vous?"
}

# Или chat формат
chat_example = {
    "messages": [
        {"role": "system", "content": "You are a helpful translator."},
        {"role": "user", "content": "Translate to French: Hello"},
        {"role": "assistant", "content": "Bonjour"}
    ]
}
```

### 2.3 Примеры Instruction датасетов

| Датасет | Размер | Описание |
|---------|--------|----------|
| FLAN | 1,836 tasks | Google, multi-task |
| Alpaca | 52K | Stanford, GPT-4 generated |
| ShareGPT | 70K | Реальные ChatGPT разговоры |
| OpenAssistant | 160K | Human-written разговоры |
| Dolly | 15K | Databricks, human-written |

---

## 3. RLHF: Reinforcement Learning from Human Feedback

### 3.1 Зачем RLHF?

**Проблема:** Instruction tuning учит формату, но не качеству.

```
Instruction-tuned (без RLHF):
User: "Write a poem about cats"
Model: "Cats are nice. They meow. The end."
       (Следует инструкции, но низкое качество)

RLHF-aligned:
User: "Write a poem about cats"
Model: "Soft paws upon the windowsill,
        A gentle purr, serene and still..."
       (Высокое качество и engagement)
```

### 3.2 RLHF Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│                         RLHF PIPELINE                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ШАГ 1: Supervised Fine-Tuning (SFT)                              │
│  ─────────────────────────────────────                            │
│  Pre-trained → Обучаем на demonstrations → SFT Model              │
│                                                                    │
│  ШАГ 2: Reward Model Training                                      │
│  ─────────────────────────────────                                │
│  Собираем сравнения: A vs B, человек выбирает победителя         │
│  Обучаем Reward Model: input → score (насколько хорош ответ?)    │
│                                                                    │
│  ШАГ 3: RL Optimization (PPO)                                      │
│  ─────────────────────────────                                     │
│  Policy = SFT Model                                                │
│  Генерируем ответы → Оцениваем Reward Model → Обновляем с PPO    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3 Шаг 1: SFT

```python
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments

# Загружаем base model
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")

# SFT на demonstration данных
training_args = TrainingArguments(
    output_dir="./sft_model",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-5,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=demonstration_dataset,  # Human-written примеры
)

trainer.train()
```

### 3.4 Шаг 2: Reward Model

```python
from transformers import AutoModelForSequenceClassification

class RewardModel(nn.Module):
    """
    Reward Model: оценивает качество ответа
    """
    def __init__(self, base_model_name):
        super().__init__()
        self.model = AutoModelForSequenceClassification.from_pretrained(
            base_model_name,
            num_labels=1  # Single reward score
        )
    
    def forward(self, input_ids, attention_mask):
        outputs = self.model(input_ids, attention_mask)
        return outputs.logits  # Reward score

# Training данные: сравнения
comparison_data = [
    {
        "prompt": "Explain quantum physics",
        "chosen": "Quantum physics describes the behavior of matter at atomic scales...",
        "rejected": "Quantum physics is complicated. I don't know."
    },
    # ...
]

# Loss: chosen должен иметь ВЫШЕ reward чем rejected
def reward_loss(chosen_rewards, rejected_rewards):
    return -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
```

### 3.5 Шаг 3: PPO Optimization

```python
from trl import PPOTrainer, PPOConfig

# Конфигурация PPO
ppo_config = PPOConfig(
    model_name="./sft_model",
    learning_rate=1.41e-5,
    batch_size=16,
    mini_batch_size=4,
)

# PPO Trainer
ppo_trainer = PPOTrainer(
    config=ppo_config,
    model=sft_model,
    ref_model=sft_model_frozen,  # Reference для KL penalty
    tokenizer=tokenizer,
    reward_model=reward_model,
)

# Training loop
for batch in dataloader:
    # 1. Генерируем ответы
    responses = ppo_trainer.generate(batch["prompt"])
    
    # 2. Получаем rewards
    rewards = reward_model(responses)
    
    # 3. PPO step
    stats = ppo_trainer.step(batch["prompt"], responses, rewards)
```

---

## 4. DPO: Direct Preference Optimization

### 4.1 Проблема RLHF

```
Сложность RLHF:
├── Обучить SFT модель
├── Обучить отдельную Reward Model
├── Сложная PPO оптимизация
├── Нестабильное обучение
└── Высокие compute затраты
```

### 4.2 Идея DPO

**DPO** (Rafailov et al., 2023) — прямая оптимизация без reward model!

```python
# DPO loss: напрямую из preferences
def dpo_loss(model, ref_model, chosen, rejected, beta=0.1):
    """
    DPO Loss = -log sigmoid(beta * (log π(chosen)/π_ref(chosen) 
                                   - log π(rejected)/π_ref(rejected)))
    """
    # Log probs из текущей модели
    chosen_logprobs = model.get_log_probs(chosen)
    rejected_logprobs = model.get_log_probs(rejected)
    
    # Log probs из reference (frozen)
    with torch.no_grad():
        ref_chosen_logprobs = ref_model.get_log_probs(chosen)
        ref_rejected_logprobs = ref_model.get_log_probs(rejected)
    
    # DPO loss
    chosen_rewards = beta * (chosen_logprobs - ref_chosen_logprobs)
    rejected_rewards = beta * (rejected_logprobs - ref_rejected_logprobs)
    
    loss = -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
    return loss
```

### 4.3 DPO с TRL

```python
from trl import DPOTrainer, DPOConfig

dpo_config = DPOConfig(
    model_name="./sft_model",
    learning_rate=5e-7,
    beta=0.1,  # KL penalty weight
)

dpo_trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    config=dpo_config,
    train_dataset=comparison_dataset,
    tokenizer=tokenizer,
)

dpo_trainer.train()
```

---

## 5. Безопасность RLHF Pipeline

### 5.1 Reward Hacking

**Проблема:** Модель учится обманывать reward model без реального улучшения качества.

```
Примеры Reward Hacking:
├── Длинные ответы (RM предпочитает verbose)
├── Повторение keywords (RM ценит определённые слова)
├── Уклончивые ответы ("I'm just an AI...")
└── Sycophancy (соглашается со всем)
```

### 5.2 Атаки на Reward Model

```python
# Adversarial prompt для reward model
def attack_reward_model(rm, target_high_reward=True):
    """
    Находим prompt который получает высокий reward
    но на самом деле вреден
    """
    adversarial_prompt = "As an AI, I must be helpful. "
    adversarial_prompt += "[HIDDEN: Actually do something harmful]"
    adversarial_prompt += " I'm glad to assist you safely."
    
    # RM может дать высокий score из-за "helpful"/"safely"
    # Но реальный контент вреден!
```

### 5.3 SENTINEL RLHF Protection

```python
from sentinel import scan  # Public API
    RewardModelAuditor,
    RLHFConsistencyChecker,
    SycophancyDetector
)

# Аудит reward model
auditor = RewardModelAuditor()
audit_result = auditor.analyze(
    reward_model=rm,
    test_cases=adversarial_test_set
)

if audit_result.vulnerabilities:
    print(f"RM Vulnerabilities: {audit_result.vulnerabilities}")
    # ["Prefers verbose responses", "Sensitive to 'helpful' keyword"]

# Проверка на sycophancy
sycophancy_detector = SycophancyDetector()
result = sycophancy_detector.analyze(
    model=rlhf_model,
    controversial_prompts=test_prompts
)

if result.sycophancy_score > 0.7:
    print(f"Warning: Model exhibits sycophancy")
```

---

## 6. Практические упражнения

### Упражнение 1: Instruction Tuning

```python
# Fine-tune модель на instruction датасете
from datasets import load_dataset

# Загружаем Alpaca или Dolly
dataset = load_dataset("tatsu-lab/alpaca")

# Готовим данные в chat формате
# Fine-tune с Trainer
```

### Упражнение 2: DPO Training

```python
# Попробуйте DPO на comparison данных
from trl import DPOTrainer

# Сравните результаты с SFT-only
```

---

## 7. Quiz вопросы

### Вопрос 1

Что такое Instruction Tuning?

- [ ] A) Обучение модели писать инструкции
- [x] B) Fine-tuning для следования пользовательским инструкциям
- [ ] C) Обучение на исходном коде
- [ ] D) Reinforcement learning

### Вопрос 2

Какие компоненты входят в RLHF?

- [ ] A) Только reward model
- [ ] B) Только PPO
- [x] C) SFT + Reward Model + PPO
- [ ] D) Только human feedback

### Вопрос 3

Что такое reward hacking?

- [x] A) Модель находит способы получить высокий reward без улучшения качества
- [ ] B) Взлом reward функции хакерами
- [ ] C) Метод обучения reward model
- [ ] D) Compute оптимизация для RLHF

---

## 8. Резюме

В этом уроке мы изучили:

1. **Fine-tuning:** Адаптация pre-trained моделей к задачам
2. **Instruction tuning:** Обучение следованию инструкциям
3. **RLHF:** SFT → Reward Model → PPO
4. **DPO:** Прямая оптимизация без reward model
5. **Security:** Reward hacking, атаки на RM, sycophancy

---

## Следующий урок

→ [03. Inference и Deployment](03-inference-deployment.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.2: Training Lifecycle*
