# Fine-Tuning Implementation Fix

## Problem

The RemoteFineTuner was attempting to use `ollama fine-tune` command, which **does not exist**. Ollama is designed for model inference only, not training.

Error encountered:
```
Error: unknown flag: --fine-tune
```

## Solution

Updated RemoteFineTuner to use **Hugging Face Transformers** for actual fine-tuning on the GPU server, which is the correct approach for fine-tuning LLMs.

### Architecture

```
┌─────────────────────────────┐
│  Local Machine              │
│  ┌─────────────────────┐    │
│  │ Training Data       │    │
│  │ (JSONL format)      │    │
│  └─────────────────────┘    │
│           │ (SCP)            │
└───────────┼──────────────────┘
            │
            ▼
┌─────────────────────────────┐
│  GPU Server                 │
│  ┌─────────────────────┐    │
│  │ Fine-tuning Script  │    │
│  │ (HF Transformers)   │    │
│  ├─────────────────────┤    │
│  │ ├─ Load Model       │    │
│  │ ├─ Load Dataset     │    │
│  │ ├─ Tokenize        │    │
│  │ ├─ Train (GPU)     │    │
│  │ └─ Save Model      │    │
│  └─────────────────────┘    │
│           │                  │
│           ▼                  │
│  ┌─────────────────────┐    │
│  │ Fine-tuned Model    │    │
│  │ (HF format)         │    │
│  └─────────────────────┘    │
│           │                  │
│  (Optional: Import to Ollama)│
│           │                  │
│           ▼                  │
│  ┌─────────────────────┐    │
│  │ Ollama Model        │    │
│  │ (via Modelfile)     │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

## Implementation Details

### 1. Script Generation

The `RemoteFineTuner.fine_tune_ollama()` method now:

1. **Generates a Python fine-tuning script** with:
   - Hugging Face Transformers for training
   - JSONL dataset loading with multiple format support
   - 4-bit quantization for lower memory usage
   - Proper error handling and logging
   - Training progress monitoring
   - Post-training import instructions for Ollama

2. **Uploads the script** to the remote server via SCP

3. **Executes the script** remotely via SSH

### 2. JSONL Format Support

The fine-tuning script handles multiple JSONL formats:

**Format 1: Text-only**
```json
{"text": "This is training data"}
```

**Format 2: Prompt-Completion**
```json
{"prompt": "Q: What is AI?", "completion": "A: Artificial Intelligence is..."}
```

**Format 3: Content field**
```json
{"content": "Training example text"}
```

**Format 4: Generic JSON**
```json
{"any": "data", "will": "be converted to string"}
```

### 3. Memory Optimization

The script automatically uses 4-bit quantization when CUDA is available:

```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
```

This reduces VRAM requirements significantly:
- 7B model: ~24GB without quantization → ~6GB with 4-bit quantization
- 13B model: ~40GB without → ~12GB with 4-bit quantization

### 4. Output

The script saves the fine-tuned model in Hugging Face format:
```
fine-tuned-model/
├── config.json
├── pytorch_model.bin (or model.safetensors)
├── tokenizer.json
├── special_tokens_map.json
└── ...
```

### 5. Optional Ollama Integration

After fine-tuning, you can optionally import the model into Ollama using a Modelfile:

```dockerfile
FROM /path/to/fine-tuned-model

PARAMETER temperature 0.7
PARAMETER num_ctx 4096
```

Then:
```bash
ollama create my-finetuned-model -f ./Modelfile
ollama run my-finetuned-model
```

## Code Changes

### Updated Methods

**`fine_tune_ollama(config)`** (was broken)
- Now generates and uploads a fine-tuning script
- Executes it remotely
- Returns training results

**Removed** `_build_finetune_cmd()` (was invalid)
- Was trying to use non-existent `ollama fine-tune` flag

**Added** `_generate_finetune_script(config, dataset_path)`
- Generates Python code for Hugging Face Transformers training
- Handles multiple JSONL formats
- Includes 4-bit quantization
- Provides Ollama integration instructions

### Key Implementation

```python
def fine_tune_ollama(self, config: FineTuningConfig):
    # 1. Upload dataset
    success, remote_dataset_path = self.upload_dataset(...)

    # 2. Generate fine-tuning script
    script_content = self._generate_finetune_script(config, remote_dataset_path)

    # 3. Upload script to remote server
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
        f.write(script_content)
        scp_cmd = self._build_scp_cmd(f.name, remote_script_path, upload=True)
        subprocess.run(scp_cmd, ...)

    # 4. Execute script remotely
    cmd = f"cd {self.config.remote_data_dir} && python finetune_script.py"
    ssh_cmd = self._build_ssh_cmd(cmd)
    result = self._run_with_monitoring(ssh_cmd, config.model_name)
```

## Usage

No changes needed to the command-line interface:

```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model meta-llama/Llama-2-7b \
  --dataset data/training_data.jsonl
```

The script now properly:
1. Generates fine-tuning code
2. Uploads it to the GPU server
3. Runs actual training
4. Saves the fine-tuned model

## Supported Models

Any model on Hugging Face Hub can be fine-tuned:

**Open models (no auth needed):**
- `meta-llama/Llama-2-7b`
- `mistralai/Mistral-7B`
- `meta-llama/Llama-3-8b`
- `meta-llama/Llama-3-70b`
- `NousResearch/Nous-Hermes-2-Mistral-7B-DPO`

**Gated models (require login):**
- `meta-llama/Llama-2-13b` (requires access)
- `meta-llama/Llama-3-70b` (requires access)

To use gated models, first login:
```bash
huggingface-cli login
# Paste your access token
```

## Dependencies

The fine-tuning script requires:

```bash
pip install transformers datasets torch bitsandbytes
```

On the remote GPU server, install with:
```bash
ssh mcstar@1.tcp.ngrok.io
pip install transformers datasets torch bitsandbytes
```

Or add to your remote setup script.

## Training Duration

Estimated training time with A100 GPU:

| Model | Dataset Size | Batch | Epochs | Time  |
|-------|--------------|-------|--------|-------|
| 7B    | 100 examples | 4     | 3      | ~5m   |
| 7B    | 1K examples  | 8     | 3      | ~30m  |
| 7B    | 10K examples | 16    | 3      | ~3h   |
| 13B   | 1K examples  | 4     | 3      | ~30m  |
| 13B   | 10K examples | 8     | 3      | ~2h   |

With 4-bit quantization, training is ~2x faster and uses 4x less memory.

## Troubleshooting

### Missing Dependencies

```
ImportError: No module named 'transformers'
```

Fix on remote server:
```bash
ssh mcstar@1.tcp.ngrok.io
pip install transformers datasets torch bitsandbytes
```

### Model Not Found

```
Model not found on HuggingFace Hub: my_model_name
```

Use full Hugging Face model ID:
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model meta-llama/Llama-2-7b \
  --dataset data/training_data.jsonl
```

### Out of Memory

Reduce batch size:
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model meta-llama/Llama-2-7b \
  --dataset data/training_data.jsonl \
  --batch-size 4
```

Or use fewer epochs:
```bash
--epochs 1 --batch-size 16
```

### Dataset Format Issue

Make sure dataset is valid JSONL:
```bash
python -c "
import json
with open('data/training_data.jsonl') as f:
    for i, line in enumerate(f):
        try:
            json.loads(line)
        except:
            print(f'Invalid JSON at line {i+1}: {line}')
"
```

## Files Modified

- `mcp_client_for_ollama/training/remote_fine_tuner.py`
  - Updated `fine_tune_ollama()` method
  - Replaced `_build_finetune_cmd()` with `_generate_finetune_script()`
  - Added proper script upload via SCP

## Next Steps

1. **Verify Transformers installed on GPU server:**
   ```bash
   ssh mcstar@1.tcp.ngrok.io "python -c 'import transformers; print(transformers.__version__)'"
   ```

2. **Run fine-tuning:**
   ```bash
   python scripts/run_remote_finetuning.py \
     --config config-remote-finetune.json \
     --model meta-llama/Llama-2-7b \
     --dataset data/training_data.jsonl
   ```

3. **Monitor on GPU server:**
   ```bash
   ssh mcstar@1.tcp.ngrok.io "watch -n 1 nvidia-smi"
   ```

4. **After fine-tuning, optionally import to Ollama:**
   ```bash
   # On GPU server:
   cd ./fine-tuned-model
   cat > Modelfile << 'EOF'
   FROM .
   PARAMETER temperature 0.7
   PARAMETER num_ctx 4096
   EOF

   ollama create my-finetuned-model -f ./Modelfile
   ```

## References

- [Hugging Face Transformers Fine-tuning Guide](https://huggingface.co/docs/transformers/training)
- [Hugging Face Datasets Documentation](https://huggingface.co/docs/datasets/)
- [BitsAndBytes 4-bit Quantization](https://huggingface.co/docs/transformers/main/en/quantization#bitsandbytes-integration)
- [Ollama Model File Documentation](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
