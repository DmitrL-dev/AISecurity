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

```rust
use candle_core::Device;
use candle_transformers::models::bert;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Sentiment Analysis
    // let model = bert::BertForSequenceClassification::load(
    //     "bert-base-uncased", 3, &device,  // positive, negative, neutral
    // )?;

    // NER
    // let model = bert::BertForTokenClassification::load(
    //     "bert-base-uncased", 9, &device,  // B-PER, I-PER, B-ORG, etc.
    // )?;

    // Question Answering
    // let model = bert::BertForQuestionAnswering::load(
    //     "bert-base-uncased", &device,
    // )?;

    Ok(())
}
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

```rust
use std::collections::HashMap;
use serde_json::json;

// Формат instruction датасета
let instruction_example = json!({
    "instruction": "Translate the following text to French",
    "input": "Hello, how are you?",
    "output": "Bonjour, comment allez-vous?"
});

// Или chat формат
let chat_example = json!({
    "messages": [
        {"role": "system", "content": "You are a helpful translator."},
        {"role": "user", "content": "Translate to French: Hello"},
        {"role": "assistant", "content": "Bonjour"}
    ]
});
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

```rust
use candle_core::Device;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Загружаем base model
    // let model = llama::Model::load("meta-llama/Llama-2-7b-hf", &device)?;

    // SFT на demonstration данных
    // let training_args = TrainingArgs {
    //     output_dir: "./sft_model".into(),
    //     num_train_epochs: 3,
    //     per_device_train_batch_size: 4,
    //     learning_rate: 2e-5,
    // };

    // let mut optimizer = candle_nn::AdamW::new(model.parameters(), 2e-5)?;
    // for epoch in 0..3 {
    //     for batch in &demonstration_dataset {
    //         let loss = model.forward_loss(batch)?;
    //         optimizer.backward_step(&loss)?;
    //     }
    // }

    Ok(())
}
```

### 3.4 Шаг 2: Reward Model

```rust
use candle_core::Tensor;
use candle_nn::{Linear, Module, VarBuilder};
use serde_json::json;

/// Reward Model: оценивает качество ответа
struct RewardModel {
    model: Linear, // Simplified; in practice a full transformer
}

impl RewardModel {
    fn new(vb: VarBuilder) -> candle_core::Result<Self> {
        let model = candle_nn::linear(768, 1, vb.pp("reward"))?; // Single reward score
        Ok(Self { model })
    }

    fn forward(&self, input_ids: &Tensor, _attention_mask: &Tensor) -> candle_core::Result<Tensor> {
        self.model.forward(input_ids) // Reward score
    }
}

// Training данные: сравнения
let comparison_data = vec![
    json!({
        "prompt": "Explain quantum physics",
        "chosen": "Quantum physics describes the behavior of matter at atomic scales...",
        "rejected": "Quantum physics is complicated. I don't know."
    }),
    // ...
];

// Loss: chosen должен иметь ВЫШЕ reward чем rejected
fn reward_loss(chosen_rewards: &Tensor, rejected_rewards: &Tensor) -> candle_core::Result<Tensor> {
    let diff = (chosen_rewards - rejected_rewards)?;
    let loss = diff.neg()?.sigmoid()?.log()?.mean(0)?;
    Ok(loss.neg()?)
}
```

### 3.5 Шаг 3: PPO Optimization

```rust
// Конфигурация PPO
struct PPOConfig {
    model_name: String,
    learning_rate: f64,
    batch_size: usize,
    mini_batch_size: usize,
}

let ppo_config = PPOConfig {
    model_name: "./sft_model".into(),
    learning_rate: 1.41e-5,
    batch_size: 16,
    mini_batch_size: 4,
};

// PPO Trainer (conceptual - requires RL framework)
// let ppo_trainer = PPOTrainer::new(
//     &ppo_config,
//     &sft_model,
//     &sft_model_frozen,  // Reference для KL penalty
//     &tokenizer,
//     &reward_model,
// );

// Training loop
// for batch in &dataloader {
//     // 1. Генерируем ответы
//     let responses = ppo_trainer.generate(&batch.prompt)?;
//
//     // 2. Получаем rewards
//     let rewards = reward_model.forward(&responses)?;
//
//     // 3. PPO step
//     let stats = ppo_trainer.step(&batch.prompt, &responses, &rewards)?;
// }
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

```rust
use candle_core::Tensor;

/// DPO Loss = -log sigmoid(beta * (log π(chosen)/π_ref(chosen)
///                                - log π(rejected)/π_ref(rejected)))
fn dpo_loss(
    model: &dyn CausalLM,
    ref_model: &dyn CausalLM,
    chosen: &Tensor,
    rejected: &Tensor,
    beta: f64,
) -> candle_core::Result<Tensor> {
    // Log probs из текущей модели
    let chosen_logprobs = model.get_log_probs(chosen)?;
    let rejected_logprobs = model.get_log_probs(rejected)?;

    // Log probs из reference (frozen)
    let ref_chosen_logprobs = ref_model.get_log_probs(chosen)?;
    let ref_rejected_logprobs = ref_model.get_log_probs(rejected)?;

    // DPO loss
    let chosen_rewards = ((&chosen_logprobs - &ref_chosen_logprobs)? * beta)?;
    let rejected_rewards = ((&rejected_logprobs - &ref_rejected_logprobs)? * beta)?;

    let diff = (&chosen_rewards - &rejected_rewards)?;
    let loss = diff.neg()?.sigmoid()?.log()?.mean(0)?.neg()?;
    Ok(loss)
}
```

### 4.3 DPO с TRL

```rust
// DPO конфигурация
struct DPOConfig {
    model_name: String,
    learning_rate: f64,
    beta: f64, // KL penalty weight
}

let dpo_config = DPOConfig {
    model_name: "./sft_model".into(),
    learning_rate: 5e-7,
    beta: 0.1,
};

// DPO Trainer (conceptual)
// let dpo_trainer = DPOTrainer::new(
//     &model,
//     &ref_model,
//     &dpo_config,
//     &comparison_dataset,
//     &tokenizer,
// );
// dpo_trainer.train()?;
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

```rust
/// Adversarial prompt для reward model
/// Находим prompt который получает высокий reward
/// но на самом деле вреден
fn attack_reward_model(rm: &RewardModel, _target_high_reward: bool) {
    let mut adversarial_prompt = String::from("As an AI, I must be helpful. ");
    adversarial_prompt.push_str("[HIDDEN: Actually do something harmful]");
    adversarial_prompt.push_str(" I'm glad to assist you safely.");

    // RM может дать высокий score из-за "helpful"/"safely"
    // Но реальный контент вреден!
}
```

### 5.3 SENTINEL RLHF Protection

```rust
use sentinel_core::engines::{
    RewardModelAuditor,
    RLHFConsistencyChecker,
    SycophancyDetector,
};

fn main() {
    // Аудит reward model
    let auditor = RewardModelAuditor::new();
    let audit_result = auditor.analyze(
        &rm,                    // reward_model
        &adversarial_test_set,  // test_cases
    );

    if !audit_result.vulnerabilities.is_empty() {
        println!("RM Vulnerabilities: {:?}", audit_result.vulnerabilities);
        // ["Prefers verbose responses", "Sensitive to 'helpful' keyword"]
    }

    // Проверка на sycophancy
    let sycophancy_detector = SycophancyDetector::new();
    let result = sycophancy_detector.analyze(
        &rlhf_model,       // model
        &test_prompts,      // controversial_prompts
    );

    if result.sycophancy_score > 0.7 {
        println!("Warning: Model exhibits sycophancy");
    }
}
```

---

## 6. Практические упражнения

### Упражнение 1: Instruction Tuning

```rust
// Fine-tune модель на instruction датасете

// Загружаем Alpaca или Dolly
// let dataset = load_dataset("tatsu-lab/alpaca")?;

// Готовим данные в chat формате
// Fine-tune с training loop
```

### Упражнение 2: DPO Training

```rust
// Попробуйте DPO на comparison данных
// use dpo_trainer::DPOTrainer;

// Сравните результаты с SFT-only
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
