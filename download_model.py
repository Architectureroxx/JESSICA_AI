import os
from huggingface_hub import hf_hub_download

# Ensure the local models directory exists
os.makedirs("models", exist_ok=True)

print("[Downloading] Fetching Llama-3 model from Hugging Face... This may take a while.")

model_path = hf_hub_download(
    repo_id="lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
    filename="Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
    local_dir="models"
)

print(f"[Success] Model downloaded and saved to: {model_path}")