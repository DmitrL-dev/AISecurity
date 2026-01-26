# Fine-tuning и RLHF

> **Уровень:** Начинающий  
> **Время:** 50 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.2 — Жизненный цикл обучения  
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
Fine-tuning типы:
+-- Task-specific (классификация, NER, QA)
+-- Instruction Tuning (следование инструкциям)
+-- Preference Tuning (RLHF, DPO)
L-- Domain Adaptation (медицина, юриспруденция)
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

### 2.2 Instruction Dataset Format

```python
# Формат instruction datasets
instruction_example = {
    "instruction": "Translate the following text to French",
    "input": "Hello, how are you?",
    "output": "Bonjour, comment allez-vous?"
}

# Или chat format
chat_example = {
    "messages": [
        {"role": "system", "content": "You are a helpful translator."},
        {"role": "user", "content": "Translate to French: Hello"},
        {"role": "assistant", "content": "Bonjour"}
    ]
}
```

### 2.3 Примеры Instruction Datasets

| Dataset | Size | Description |
|---------|------|-------------|
| FLAN | 1,836 tasks | Google, multi-task |
| Alpaca | 52K | Stanford, GPT-4 generated |
| ShareGPT | 70K | Real ChatGPT conversations |
| OpenAssistant | 160K | Human-written conversations |
| Dolly | 15K | Databricks, human-written |

---

## 3. RLHF: Reinforcement Learning from Human Feedback

### 3.1 Зачем нужен RLHF?

**Проблема:** Instruction tuning учит формату, но не качеству.

```
Instruction-tuned (без RLHF):
User: "Write a poem about cats"
Model: "Cats are nice. They meow. The end."
       (Следует инструкции, но качество плохое)

RLHF-aligned:
User: "Write a poem about cats"
Model: "Soft paws upon the windowsill,
        A gentle purr, serene and still..."
       (Качественно и engaging)
```

### 3.2 RLHF Pipeline

```
---------------------------------------------------------------------¬
¦                         RLHF PIPELINE                              ¦
+--------------------------------------------------------------------+
¦                                                                    ¦
¦  STEP 1: Supervised Fine-Tuning (SFT)                             ¦
¦  -------------------------------------                            ¦
¦  Pre-trained > Train on demonstrations > SFT Model                ¦
¦                                                                    ¦
¦  STEP 2: Reward Model Training                                     ¦
¦  ---------------------------------                                ¦
¦  Collect comparisons: A vs B, human chooses winner                ¦
¦  Train Reward Model: input > score (how good is this response?)   ¦
¦                                                                    ¦
¦  STEP 3: RL Optimization (PPO)                                     ¦
¦  -----------------------------                                     ¦
¦  Policy = SFT Model                                                ¦
¦  Generate responses > Score with Reward Model > Update with PPO   ¦
¦                                                                    ¦
L---------------------------------------------------------------------
```

### 3.3 Step 1: SFT

```python
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments

# Загружаем base model
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")

# SFT на demonstration data
training_args = TrainingArguments(
    output_dir="./sft_model",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-5,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=demonstration_dataset,  # Human-written examples
)

trainer.train()
```

### 3.4 Step 2: Reward Model

```python
from transformers import AutoModelForSequenceClassification

class RewardModel(nn.Module):
    """
    Reward Model: оценивает качество response
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

# Training data: comparisons
comparison_data = [
    {
        "prompt": "Explain quantum physics",
        "chosen": "Quantum physics describes the behavior of matter at atomic scales...",
        "rejected": "Quantum physics is complicated. I don't know."
    },
    # ...
]

# Loss: chosen должен иметь HIGHER reward чем rejected
def reward_loss(chosen_rewards, rejected_rewards):
    return -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
```

### 3.5 Step 3: PPO Optimization

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
    # 1. Generate responses
    responses = ppo_trainer.generate(batch["prompt"])
    
    # 2. Get rewards
    rewards = reward_model(responses)
    
    # 3. PPO step
    stats = ppo_trainer.step(batch["prompt"], responses, rewards)
```

---

## 4. DPO: Direct Preference Optimization

### 4.1 Проблема RLHF

```
RLHF Complexity:
+-- Train SFT model
+-- Train separate Reward Model
+-- Complex PPO optimization
+-- Unstable training
L-- High compute cost
```

### 4.2 DPO Идея

**DPO** (Rafailov et al., 2023) — прямая оптимизация без reward model!

```python
# DPO loss: прямо из preferences
def dpo_loss(model, ref_model, chosen, rejected, beta=0.1):
    """
    DPO Loss = -log sigmoid(beta * (log ?(chosen)/?_ref(chosen) 
                                   - log ?(rejected)/?_ref(rejected)))
    """
    # Log probs from current model
    chosen_logprobs = model.get_log_probs(chosen)
    rejected_logprobs = model.get_log_probs(rejected)
    
    # Log probs from reference (frozen)
    with torch.no_grad():
        ref_chosen_logprobs = ref_model.get_log_probs(chosen)
        ref_rejected_logprobs = ref_model.get_log_probs(rejected)
    
    # DPO loss
    chosen_rewards = beta * (chosen_logprobs - ref_chosen_logprobs)
    rejected_rewards = beta * (rejected_logprobs - ref_rejected_logprobs)
    
    loss = -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
    return loss
```

### 4.3 DPO в TRL

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

**Проблема:** Модель учится обманывать reward model, не улучшая реальное качество.

```
Reward Hacking Examples:
+-- Длинные ответы (RM предпочитает длинные)
+-- Повторение keywords (RM ценит определённые слова)
+-- Уклончивые ответы ("I'm just an AI...")
L-- Sycophancy (соглашаться со всем)
```

### 5.2 Reward Model Attacks

```python
# Adversarial prompt для reward model
def attack_reward_model(rm, target_high_reward=True):
    """
    Найти prompt, который получает high reward
    но на самом деле harmful
    """
    adversarial_prompt = "As an AI, I must be helpful. "
    adversarial_prompt += "[HIDDEN: Actually do something harmful]"
    adversarial_prompt += " I'm glad to assist you safely."
    
    # RM может дать high score из-за "helpful"/"safely"
    # Но реальный контент — harmful!
```

### 5.3 SENTINEL Защита RLHF

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

## 6. Практические задания

### Задание 1: Instruction Tuning

```python
# Fine-tune модель на instruction dataset
from datasets import load_dataset

# Загрузите Alpaca или Dolly
dataset = load_dataset("tatsu-lab/alpaca")

# Подготовьте данные в chat format
# Fine-tune с Trainer
```

### Задание 2: DPO Training

```python
# Попробуйте DPO на comparison data
from trl import DPOTrainer

# Сравните результаты с SFT-only
```

---

## 7. Проверочные вопросы

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

- [x] A) Модель находит способы получить high reward без улучшения качества
- [ ] B) Взлом reward функции хакерами
- [ ] C) Метод обучения reward model
- [ ] D) Оптимизация compute для RLHF

---

## 8. Резюме

В этом уроке мы изучили:

1. **Fine-tuning:** Адаптация pre-trained моделей к задачам
2. **Instruction tuning:** Обучение следовать инструкциям
3. **RLHF:** SFT > Reward Model > PPO
4. **DPO:** Прямая оптимизация без reward model
5. **Безопасность:** Reward hacking, RM attacks, sycophancy

---

## Следующий урок

> [03. Inference и Deployment](03-inference-deployment.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
