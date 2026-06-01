from unsloth import FastLanguageModel
from trl import SFTTrainer
from datasets import load_dataset

# Load your local base model (TinyLlama to fit in 4GB VRAM)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/tinyllama-chat",
    load_in_4bit = True,
    device_map = {"": 0},
    max_seq_length = 512,
)

# Apply LoRA target modules
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha = 16,
)

import json
import datasets
from datasets import Dataset

# MONKEY-PATCH to bypass Python 3.14 dill serialization bug
datasets.fingerprint.generate_fingerprint = lambda *args, **kwargs: "alas_mock_fingerprint_v1"

# Load the dataset manually
with open("alas_dataset.jsonl", "r") as f:
    data = [json.loads(line) for line in f]
alas_dataset = Dataset.from_list(data)

# Train using your ALAS dataset
trainer = SFTTrainer(
    model = model,
    train_dataset = alas_dataset,
    dataset_text_field = "text",
    max_seq_length = 512,
)
trainer.train()

# Save the adapter weights
model.save_pretrained("backend/data/lora_adapters/alas_v1")
