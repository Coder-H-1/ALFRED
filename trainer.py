# ====== INSTALL DEPENDENCIES ======
import os
os.environ["WANDB_DISABLED"] = "true"

!pip install -U transformers accelerate datasets peft trl bitsandbytes sentencepiece

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

# =========================
# CONFIG
# =========================
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DATASET_NAME = "WNT3D/Ultimate-Offensive-Red-Team"

MAX_SEQ_LEN = 1024
BATCH_SIZE = 4
GRAD_ACCUM = 8
EPOCHS = 2
LR = 2e-4

# Reduce dataset for speed (change or remove)
DATASET_FRACTION = 0.2   # 30% of dataset (FAST)

OUTPUT_DIR = "/content/qwen2.5-redteam-lora"

# =========================
# TOKENIZER
# =========================
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.model_max_length = 1024

# =========================
# DATASET
# =========================
dataset = load_dataset(DATASET_NAME, split="train")

# Reduce samples for speed
dataset = dataset.shuffle(seed=42)
dataset = dataset.select(range(int(len(dataset) * DATASET_FRACTION)))

import json

def format_prompt(example):
    return (
        "### Instruction:\n"
        + example["instruction"]
        + "\n\n### Input:\n"
        + str(example["input"])
        + "\n\n### Response:\n"
        + str(example["output"])
    )

dataset = dataset.map(
    lambda x: {"text": format_prompt(x)},
    remove_columns=dataset.column_names,
    desc="Formatting dataset to text",
)


# =========================
# MODEL (FP16 ONLY)
# =========================
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,   # ✅ FP16
    device_map="auto",
    trust_remote_code=True,
)

model.gradient_checkpointing_enable()
model.config.use_cache = False  # REQUIRED for checkpointing

# =========================
# LORA CONFIG (FAST + SAFE)
# =========================
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# =========================
# TRAINING ARGS (NO BF16)
# =========================
from trl import SFTTrainer, SFTConfig

sft_config = SFTConfig(
    output_dir=OUTPUT_DIR,

    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    num_train_epochs=EPOCHS,
    learning_rate=LR,

    fp16=True,
    bf16=False,

    logging_steps=20,
    save_steps=500,
    save_total_limit=2,

    optim="adamw_torch",
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,

    packing=True,
    dataset_text_field="text",   # ✅ THIS IS REQUIRED

    report_to="none",
)


# =========================
# TRAINER
# =========================
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=sft_config,
)


trainer.train()

# =========================
# SAVE
# =========================
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
