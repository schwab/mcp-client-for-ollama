# Remote Fine-Tuning Guide

## Overview

The remote fine-tuning system allows you to run actual model fine-tuning on a GPU-equipped server via SSH using Hugging Face Transformers. This enables real training on powerful hardware without needing GPUs on your local machine.

### Important: Ollama Fine-Tuning

**Ollama does not support fine-tuning.** This system uses Hugging Face Transformers for fine-tuning, then optionally imports the result into Ollama for inference.

See [Finetuning Implementation Fix](./FINETUNING_IMPLEMENTATION_FIX.md) for detailed explanation and troubleshooting.

## Architecture

```
Local Machine                    GPU Server
┌─────────────────┐            ┌──────────────┐
│  Improvement    │            │              │
│  Pipeline       │            │  Ollama with │
│                 │            │  GPU Support │
│  ├─ Dataset Gen │─── SCP ───>│              │
│  ├─ Remote      │            │  ├─ Receive  │
│  │  Tuner       │            │  │  Dataset  │
│  └─ Monitor     │<── SSH ────│  ├─ Run Fine │
│                 │            │  │  Tuning   │
└─────────────────┘            │  └─ Export   │
                               │     Model    │
                               └──────────────┘
```

## Setup

### 1. SSH Key Configuration

Ensure you have SSH key-based authentication set up:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -f ~/.ssh/id_rsa -N ""

# Copy to remote server
ssh-copy-id -i ~/.ssh/id_rsa mcstar@1.tcp.ngroi.io

# Test connection
ssh mcstar@1.tcp.ngroi.io "echo 'Connection successful'"
```

### 2. Remote Server Requirements

The GPU server should have:
- Ollama installed with GPU support
- CUDA/ROCm properly configured
- Sufficient disk space for models and datasets
- Python 3.9+ (if using script-based fine-tuning)

Verify:
```bash
ssh mcstar@1.tcp.ngroi.io "ollama list && nvidia-smi"
```

### 3. Local Configuration

Copy the example config and customize:

```bash
cp config.remote-finetune.example.json config.remote-finetune.json
```

Edit `config.remote-finetune.json`:
```json
{
  "remote_gpu_server": {
    "enabled": true,
    "host": "1.tcp.ngroi.io",
    "user": "mcstar",
    "port": 22,
    "identity_file": "~/.ssh/id_rsa"
  }
}
```

## Usage

### Basic Fine-Tuning

```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --dataset data/training_data_20260131_161243.jsonl \
  --epochs 3 \
  --learning-rate 0.00002
```

### Check Remote Status

```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --status-only
```

### Custom Output Model Name

```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --output-model qwen2.5-coder:32b-improved \
  --dataset data/training_data.jsonl
```

### With Configuration File

```bash
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

## Advanced Configuration

### Model-Specific Settings

Edit the config file to set model-specific fine-tuning parameters:

```json
{
  "fine_tuning": {
    "model_specific": {
      "qwen2.5-coder:32b": {
        "learning_rate": 0.00002,
        "batch_size": 8,
        "num_epochs": 3
      },
      "qwen2.5-coder:14b": {
        "learning_rate": 0.00003,
        "batch_size": 16,
        "num_epochs": 3
      }
    }
  }
}
```

### Custom Fine-Tuning Script

If you want to use a custom fine-tuning script:

1. Create your script on the remote server
2. Update config to use "script" method
3. Run fine-tuning

```json
{
  "fine_tuning": {
    "method": "script",
    "script_path": "~/scripts/fine_tune_ollama.py"
  }
}
```

## Integration with Improvement Pipeline

To integrate remote fine-tuning with the improvement pipeline, update the pipeline script:

```python
from mcp_client_for_ollama.training.remote_fine_tuner import RemoteFineTuner, RemoteConfig, FineTuningConfig

# Create remote config
remote_config = RemoteConfig(
    host="1.tcp.ngroi.io",
    user="mcstar",
    port=22,
    identity_file="~/.ssh/id_rsa"
)

# Create fine-tuner
tuner = RemoteFineTuner(remote_config)

# Fine-tune a model
ft_config = FineTuningConfig(
    model_name="qwen2.5-coder:32b",
    dataset_path="data/training_data.jsonl",
    output_model_name="qwen2.5-coder:32b-improved",
    learning_rate=2e-5,
    batch_size=16,
    num_epochs=3
)

success, result = tuner.fine_tune_ollama(ft_config)
print(f"Fine-tuning {'succeeded' if success else 'failed'}: {result}")
```

## Monitoring

### Real-time Monitoring

SSH into the remote server:

```bash
ssh mcstar@1.tcp.ngroi.io

# Watch GPU usage
watch nvidia-smi

# Monitor Ollama logs
tail -f ~/.ollama/logs/server.log

# List running models
ollama list

# Check disk usage
df -h /tmp/ollama_finetune
```

### Status Check

Check remote server health:

```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model dummy \
  --dataset dummy.jsonl \
  --status-only
```

## Troubleshooting

### SSH Connection Issues

```bash
# Test SSH with verbose output
ssh -vv mcstar@1.tcp.ngroi.io

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Verify server has your key
ssh mcstar@1.tcp.ngroi.io "cat ~/.ssh/authorized_keys | grep $(cat ~/.ssh/id_rsa.pub | awk '{print $3}')"
```

### Dataset Upload Issues

```bash
# Check remote directory permissions
ssh mcstar@1.tcp.ngroi.io "ls -la /tmp/ollama_finetune"

# Manually upload dataset
scp data/training_data.jsonl mcstar@1.tcp.ngroi.io:/tmp/ollama_finetune/

# Verify upload
ssh mcstar@1.tcp.ngroi.io "ls -lh /tmp/ollama_finetune/training_data.jsonl"
```

### Fine-Tuning Issues

```bash
# Check if Ollama is running
ssh mcstar@1.tcp.ngroi.io "ollama list"

# Check GPU availability
ssh mcstar@1.tcp.ngroi.io "nvidia-smi"

# Check disk space
ssh mcstar@1.tcp.ngroi.io "df -h"

# View Ollama logs
ssh mcstar@1.tcp.ngroi.io "tail -100 ~/.ollama/logs/server.log"
```

### Model Not Found After Fine-Tuning

```bash
# List all available models on remote
ssh mcstar@1.tcp.ngroi.io "ollama list"

# Check model directory
ssh mcstar@1.tcp.ngroi.io "ls -la ~/.ollama/models/manifests/registry.ollama.ai/library/"
```

## Best Practices

### 1. Dataset Validation

Always validate your dataset before fine-tuning:

```bash
# Check dataset format
python -c "
import json
count = 0
with open('data/training_data.jsonl') as f:
    for line in f:
        json.loads(line)
        count += 1
print(f'Valid JSONL file with {count} lines')
"
```

### 2. Start Small

Begin with smaller batches and fewer epochs:

```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:14b \
  --dataset data/training_data.jsonl \
  --epochs 1 \
  --batch-size 32
```

### 3. Monitor Progress

Keep an SSH session open to monitor:

```bash
# Terminal 1: Run fine-tuning
python scripts/run_remote_finetuning.py --host ... --model ...

# Terminal 2: Monitor GPU
ssh mcstar@1.tcp.ngroi.io "watch -n 1 'nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits'"
```

### 4. Use Appropriate Learning Rates

Smaller models may need different rates:

| Model | Learning Rate | Batch Size | Epochs |
|-------|--------------|-----------|---------|
| 32b | 2e-5 | 8 | 3 |
| 14b | 3e-5 | 16 | 3 |
| 8b | 5e-5 | 32 | 2 |
| 3b | 1e-4 | 64 | 1 |

### 5. Clean Up

After successful fine-tuning:

```bash
# Remove dataset from remote
ssh mcstar@1.tcp.ngroi.io "rm /tmp/ollama_finetune/training_data*.jsonl"

# Keep fine-tuned models
ssh mcstar@1.tcp.ngroi.io "ollama list | grep -i improved"
```

## Performance Tuning

### Batch Size Guidelines

- Larger batch size = faster training but more memory
- Start with recommended size, adjust based on GPU memory

```bash
# Check available GPU memory
ssh mcstar@1.tcp.ngroi.io "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits"
```

### Epoch Optimization

- More epochs = better convergence but longer training
- Monitor validation loss to find optimal epochs
- Typical: 1-5 epochs for fine-tuning

### Learning Rate Tuning

- Too high: Training diverges
- Too low: Training too slow
- Rule of thumb: reduce by 10x for fine-tuning vs. pre-training

## Estimated Training Times

Based on GPU and model size:

| Model | Batch | Epochs | GPU | Time |
|-------|-------|--------|-----|------|
| 3b | 64 | 1 | A100 | ~5 min |
| 8b | 32 | 2 | A100 | ~10 min |
| 14b | 16 | 3 | A100 | ~20 min |
| 32b | 8 | 3 | A100 | ~45 min |

## Next Steps

1. **Validate Setup**: Run status-only check
2. **Test with Small Dataset**: Create minimal test dataset
3. **Monitor First Fine-Tune**: Keep terminal open to watch progress
4. **Integrate with Pipeline**: Update improvement pipeline to use remote tuner
5. **Optimize Parameters**: Adjust learning rate, batch size based on results

## Support & Debugging

For issues, check:
1. SSH connection with `ssh -vv`
2. GPU availability with `nvidia-smi`
3. Ollama status with `ollama list`
4. Logs at `~/.ollama/logs/server.log`
5. Dataset validity with JSON validator
