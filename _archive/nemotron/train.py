#!/usr/bin/env python3
"""
SENTINEL Nemotron Fine-tuning Script
QLoRA fine-tuning of Nemotron 3 Nano for threat detection.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import torch
from datasets import load_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Fine-tuning configuration."""
    # Model
    model_name: str = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    max_seq_length: int = 4096
    
    # LoRA
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: tuple = ("q_proj", "v_proj", "k_proj", "o_proj")
    
    # Training
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    num_epochs: int = 3
    warmup_steps: int = 100
    max_steps: int = -1  # -1 for full training
    
    # Paths
    train_data: str = "nemotron/training_data/train_chatml.json"
    val_data: str = "nemotron/training_data/val_chatml.json"
    output_dir: str = "models/nemotron_guard_lora"
    
    # Misc
    seed: int = 42
    fp16: bool = True
    logging_steps: int = 10
    save_steps: int = 100


def setup_model(config: TrainingConfig):
    """Setup model with Unsloth optimizations."""
    from unsloth import FastLanguageModel
    
    logger.info(f"Loading {config.model_name}...")
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config.model_name,
        max_seq_length=config.max_seq_length,
        load_in_4bit=True,
        dtype=torch.float16 if config.fp16 else torch.float32,
    )
    
    # Add LoRA adapters
    logger.info("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=config.lora_r,
        target_modules=list(config.target_modules),
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=config.seed,
    )
    
    return model, tokenizer


def load_training_data(config: TrainingConfig, tokenizer):
    """Load and tokenize training data."""
    logger.info(f"Loading training data from {config.train_data}...")
    
    # Load JSON files
    train_dataset = load_dataset("json", data_files=config.train_data, split="train")
    val_dataset = load_dataset("json", data_files=config.val_data, split="train")
    
    logger.info(f"Train samples: {len(train_dataset)}")
    logger.info(f"Val samples: {len(val_dataset)}")
    
    def format_sample(sample):
        """Format sample for training."""
        messages = sample["messages"]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}
    
    train_dataset = train_dataset.map(format_sample)
    val_dataset = val_dataset.map(format_sample)
    
    return train_dataset, val_dataset


def train(config: Optional[TrainingConfig] = None):
    """Run fine-tuning."""
    if config is None:
        config = TrainingConfig()
    
    # Check GPU
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available. Fine-tuning requires GPU.")
    
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Setup
    model, tokenizer = setup_model(config)
    train_dataset, val_dataset = load_training_data(config, tokenizer)
    
    # Trainer
    from transformers import TrainingArguments
    from trl import SFTTrainer
    
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        num_train_epochs=config.num_epochs,
        max_steps=config.max_steps,
        warmup_steps=config.warmup_steps,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        fp16=config.fp16,
        seed=config.seed,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        report_to="none",
    )
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=config.max_seq_length,
        packing=False,
    )
    
    # Train
    logger.info("🚀 Starting training...")
    trainer.train()
    
    # Save
    logger.info(f"💾 Saving model to {config.output_dir}")
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    
    # Save merged model (optional, requires more VRAM)
    try:
        merged_dir = config.output_dir + "_merged"
        logger.info(f"Merging LoRA adapters to {merged_dir}")
        model.save_pretrained_merged(merged_dir, tokenizer, save_method="merged_16bit")
    except Exception as e:
        logger.warning(f"Could not save merged model: {e}")
    
    logger.info("✅ Training complete!")
    return model, tokenizer


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune Nemotron for SENTINEL")
    parser.add_argument("--train-data", default="nemotron/training_data/train_chatml.json")
    parser.add_argument("--val-data", default="nemotron/training_data/val_chatml.json")
    parser.add_argument("--output-dir", default="models/nemotron_guard_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    
    args = parser.parse_args()
    
    config = TrainingConfig(
        train_data=args.train_data,
        val_data=args.val_data,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        lora_r=args.lora_r,
    )
    
    train(config)


if __name__ == "__main__":
    main()
