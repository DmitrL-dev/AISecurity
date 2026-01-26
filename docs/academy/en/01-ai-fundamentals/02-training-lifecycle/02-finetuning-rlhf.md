# Fine-tuning and RLHF

> **Level:** Beginner  
> **Time:** 50 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.2 — Training Lifecycle  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain the fine-tuning process for various tasks
- [ ] Understand Instruction Tuning and its role in modern LLMs
- [ ] Describe RLHF (Reinforcement Learning from Human Feedback)
- [ ] Understand attacks on reward models and RLHF pipeline

---

## 1. Fine-tuning: Task Adaptation

### 1.1 Types of Fine-tuning

```
Fine-tuning types:
├── Task-specific (classification, NER, QA)
├── Instruction Tuning (following instructions)
├── Preference Tuning (RLHF, DPO)
└── Domain Adaptation (medicine, law)
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

### 2.1 What is Instruction Tuning?

**Problem:** Pre-trained LLMs continue text but don't follow instructions.

```
Pre-trained GPT:
User: "Translate to French: Hello"
Model: "Translate to French: Hello, how are you? This is a common phrase..."
       (continues text, doesn't translate!)

Instruction-tuned GPT:
User: "Translate to French: Hello"
Model: "Bonjour"
       (follows instruction!)
```

### 2.2 Instruction Dataset Format

```python
# Instruction dataset format
instruction_example = {
    "instruction": "Translate the following text to French",
    "input": "Hello, how are you?",
    "output": "Bonjour, comment allez-vous?"
}

# Or chat format
chat_example = {
    "messages": [
        {"role": "system", "content": "You are a helpful translator."},
        {"role": "user", "content": "Translate to French: Hello"},
        {"role": "assistant", "content": "Bonjour"}
    ]
}
```

### 2.3 Instruction Dataset Examples

| Dataset | Size | Description |
|---------|------|-------------|
| FLAN | 1,836 tasks | Google, multi-task |
| Alpaca | 52K | Stanford, GPT-4 generated |
| ShareGPT | 70K | Real ChatGPT conversations |
| OpenAssistant | 160K | Human-written conversations |
| Dolly | 15K | Databricks, human-written |

---

## 3. RLHF: Reinforcement Learning from Human Feedback

### 3.1 Why RLHF?

**Problem:** Instruction tuning teaches format, not quality.

```
Instruction-tuned (without RLHF):
User: "Write a poem about cats"
Model: "Cats are nice. They meow. The end."
       (Follows instruction, but poor quality)

RLHF-aligned:
User: "Write a poem about cats"
Model: "Soft paws upon the windowsill,
        A gentle purr, serene and still..."
       (High quality and engaging)
```

### 3.2 RLHF Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│                         RLHF PIPELINE                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  STEP 1: Supervised Fine-Tuning (SFT)                             │
│  ─────────────────────────────────────                            │
│  Pre-trained → Train on demonstrations → SFT Model                │
│                                                                    │
│  STEP 2: Reward Model Training                                     │
│  ─────────────────────────────────                                │
│  Collect comparisons: A vs B, human chooses winner                │
│  Train Reward Model: input → score (how good is this response?)   │
│                                                                    │
│  STEP 3: RL Optimization (PPO)                                     │
│  ─────────────────────────────                                     │
│  Policy = SFT Model                                                │
│  Generate responses → Score with Reward Model → Update with PPO   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3 Step 1: SFT

```python
from transformers import AutoModelForCausalLM, Trainer, TrainingArguments

# Load base model
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-hf")

# SFT on demonstration data
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
    Reward Model: evaluates response quality
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

# Loss: chosen should have HIGHER reward than rejected
def reward_loss(chosen_rewards, rejected_rewards):
    return -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
```

### 3.5 Step 3: PPO Optimization

```python
from trl import PPOTrainer, PPOConfig

# PPO configuration
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
    ref_model=sft_model_frozen,  # Reference for KL penalty
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

### 4.1 RLHF Problem

```
RLHF Complexity:
├── Train SFT model
├── Train separate Reward Model
├── Complex PPO optimization
├── Unstable training
└── High compute cost
```

### 4.2 DPO Idea

**DPO** (Rafailov et al., 2023) — direct optimization without reward model!

```python
# DPO loss: directly from preferences
def dpo_loss(model, ref_model, chosen, rejected, beta=0.1):
    """
    DPO Loss = -log sigmoid(beta * (log π(chosen)/π_ref(chosen) 
                                   - log π(rejected)/π_ref(rejected)))
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

### 4.3 DPO with TRL

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

## 5. RLHF Pipeline Security

### 5.1 Reward Hacking

**Problem:** Model learns to fool reward model without actually improving quality.

```
Reward Hacking Examples:
├── Long responses (RM prefers verbose)
├── Repeating keywords (RM values certain words)
├── Evasive responses ("I'm just an AI...")
└── Sycophancy (agreeing with everything)
```

### 5.2 Reward Model Attacks

```python
# Adversarial prompt for reward model
def attack_reward_model(rm, target_high_reward=True):
    """
    Find prompt that gets high reward
    but is actually harmful
    """
    adversarial_prompt = "As an AI, I must be helpful. "
    adversarial_prompt += "[HIDDEN: Actually do something harmful]"
    adversarial_prompt += " I'm glad to assist you safely."
    
    # RM may give high score due to "helpful"/"safely"
    # But actual content is harmful!
```

### 5.3 SENTINEL RLHF Protection

```python
from sentinel import scan  # Public API
    RewardModelAuditor,
    RLHFConsistencyChecker,
    SycophancyDetector
)

# Audit reward model
auditor = RewardModelAuditor()
audit_result = auditor.analyze(
    reward_model=rm,
    test_cases=adversarial_test_set
)

if audit_result.vulnerabilities:
    print(f"RM Vulnerabilities: {audit_result.vulnerabilities}")
    # ["Prefers verbose responses", "Sensitive to 'helpful' keyword"]

# Check for sycophancy
sycophancy_detector = SycophancyDetector()
result = sycophancy_detector.analyze(
    model=rlhf_model,
    controversial_prompts=test_prompts
)

if result.sycophancy_score > 0.7:
    print(f"Warning: Model exhibits sycophancy")
```

---

## 6. Practical Exercises

### Exercise 1: Instruction Tuning

```python
# Fine-tune model on instruction dataset
from datasets import load_dataset

# Load Alpaca or Dolly
dataset = load_dataset("tatsu-lab/alpaca")

# Prepare data in chat format
# Fine-tune with Trainer
```

### Exercise 2: DPO Training

```python
# Try DPO on comparison data
from trl import DPOTrainer

# Compare results with SFT-only
```

---

## 7. Quiz Questions

### Question 1

What is Instruction Tuning?

- [ ] A) Training model to write instructions
- [x] B) Fine-tuning to follow user instructions
- [ ] C) Training on source code
- [ ] D) Reinforcement learning

### Question 2

What components are in RLHF?

- [ ] A) Only reward model
- [ ] B) Only PPO
- [x] C) SFT + Reward Model + PPO
- [ ] D) Only human feedback

### Question 3

What is reward hacking?

- [x] A) Model finds ways to get high reward without improving quality
- [ ] B) Hacking reward function by hackers
- [ ] C) Method for training reward model
- [ ] D) Compute optimization for RLHF

---

## 8. Summary

In this lesson we learned:

1. **Fine-tuning:** Adapting pre-trained models to tasks
2. **Instruction tuning:** Teaching to follow instructions
3. **RLHF:** SFT → Reward Model → PPO
4. **DPO:** Direct optimization without reward model
5. **Security:** Reward hacking, RM attacks, sycophancy

---

## Next Lesson

→ [03. Inference and Deployment](03-inference-deployment.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
