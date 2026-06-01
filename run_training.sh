#!/bin/bash
echo "Installing Unsloth and Training Dependencies..."
source venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps "xformers<0.0.26" "trl<0.9.0" peft accelerate bitsandbytes datasets chromadb

echo "Dependencies installed."
echo "Running data extraction..."
python backend/queries.py

echo "Starting Unsloth Training..."
python backend/app/learning/train_unsloth.py

echo "Training complete! Adapter saved in backend/data/lora_adapters/alas_v1"
