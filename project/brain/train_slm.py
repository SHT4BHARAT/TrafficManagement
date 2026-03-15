"""
TrafficAgent SLM Fine-Tuning Script using Unsloth & QLoRA
Run this script locally on a machine with a dedicated GPU (e.g., NVIDIA RTX series).
Requires: pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
"""

import os
import torch
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# Configuration
MODEL_NAME = "unsloth/Llama-3.2-3B-Instruct" # Base model
MAX_SEQ_LENGTH = 1024
DTYPE = None # Auto detection
LOAD_IN_4BIT = True # Use QLoRA
DATASET_FILE = "traffic_dataset.jsonl"
OLLAMA_MODEL_NAME = "TrafficAgent"

def main():
    print(f"🚀 Starting SLM Fine-Tuning Process ({MODEL_NAME})...")
    
    # 1. Load Model & Tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = MAX_SEQ_LENGTH,
        dtype = DTYPE,
        load_in_4bit = LOAD_IN_4BIT,
    )

    # 2. Add LoRA Adapters (Targeting attention and MLP)
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16, # Rank
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 16,
        lora_dropout = 0, # Optimized for 0
        bias = "none",    # Optimized for "none"
        use_gradient_checkpointing = "unsloth", 
        random_state = 3407,
        use_rslora = False,
        loftq_config = None,
    )

    # 3. Load & Format Dataset
    dataset_path = os.path.join(os.path.dirname(__file__), DATASET_FILE)
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Run dataset_gen.py first.")
        
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

    EOS_TOKEN = tokenizer.eos_token
    def formatting_prompts_func(examples):
        instructions = examples["instruction"]
        inputs       = examples["input"]
        outputs      = examples["output"]
        texts = []
        for instruction, input_data, output in zip(instructions, inputs, outputs):
            # Must add EOS token, otherwise generation goes on forever!
            text = alpaca_prompt.format(instruction, input_data, output) + EOS_TOKEN
            texts.append(text)
        return { "text" : texts }

    formatted_dataset = dataset.map(formatting_prompts_func, batched = True)

    # 4. Initialize Trainer
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = formatted_dataset,
        dataset_text_field = "text",
        max_seq_length = MAX_SEQ_LENGTH,
        dataset_num_proc = 2,
        packing = False, # Can make training 5x faster for short sequences.
        args = TrainingArguments(
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 5,
            max_steps = 150, # Set to higher (e.g., 500-1000) for full training
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 10,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = "outputs",
        ),
    )

    # 5. Train
    print("🧠 Training in progress...")
    trainer_stats = trainer.train()

    # 6. Save Model to GGUF
    print("💾 Training complete. Exporting to GGUF format for Ollama...")
    export_path = os.path.join(os.path.dirname(__file__), "TrafficAgent.gguf")
    
    # Save to q4_k_m GGUF directly using Unsloth
    model.save_pretrained_gguf("TrafficAgent", tokenizer, quantization_method = "q4_k_m")
    
    print("✅ SLM Fine-tuning and export complete!")
    print("\nTo load into Ollama, create a Modelfile with:")
    print("FROM ./TrafficAgent-unsloth.Q4_K_M.gguf")
    print("\nThen run:")
    print("ollama create TrafficAgent -f Modelfile")
    

if __name__ == "__main__":
    main()
