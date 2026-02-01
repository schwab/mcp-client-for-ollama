# Remote Fine-Tuning Quick Start Guide

## Fixed! Config File Now Works

The bug in `scripts/run_remote_finetuning.py` has been fixed. Your config file now provides all server settings, and you only need to specify `--model` and `--dataset` via CLI.

## Basic Usage

```bash
# With your existing config-remote-finetune.json
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

That's it! The script will:
- Load host, user, port, and SSH key from config
- Use learning_rate, batch_size, epochs from config defaults
- Upload your dataset to the GPU server
- Run fine-tuning and monitor progress
- Report results

## Your Config File

Your `config-remote-finetune.json` contains:

```json
{
  "remote_gpu_server": {
    "host": "1.tcp.ngrok.io",
    "user": "mcstar",
    "port": 22,
    "identity_file": "~/.ssh/id_rsa",
    "remote_data_dir": "/mnt/12_tb/ollama_data/finetune",
    "remote_models_dir": "/mnt/12_tb/ollama_data/models"
  },
  "fine_tuning": {
    "defaults": {
      "learning_rate": 0.00002,
      "batch_size": 16,
      "num_epochs": 3,
      "warmup_steps": 100
    }
  }
}
```

## Common Commands

### Check Remote Server Status
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model dummy \
  --dataset dummy.jsonl \
  --status-only
```

### Fine-tune with Custom Epochs
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --epochs 5
```

### Fine-tune with Custom Learning Rate
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --learning-rate 0.00005
```

### Fine-tune with Custom Output Model Name
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --output-model qwen2.5-coder:32b-v2 \
  --dataset data/training_data.jsonl
```

### Full Control (Override All Config Defaults)
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --learning-rate 0.00001 \
  --batch-size 8 \
  --epochs 5 \
  --warmup-steps 200
```

## Argument Precedence

1. **CLI arguments** override config values
2. **Config file values** used if CLI not provided
3. **Built-in defaults** as fallback

So this command:
```bash
python scripts/run_remote_finetuning.py \
  --config config-remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training.jsonl \
  --learning-rate 0.0001
```

Will use:
- `host`: `1.tcp.ngrok.io` (from config)
- `user`: `mcstar` (from config)
- `learning_rate`: `0.0001` (from CLI, overrides config)
- `batch_size`: `16` (from config)
- `epochs`: `3` (from config)

## Required Arguments

You MUST provide:
- `--model` - Which model to fine-tune (via CLI or edit config)
- `--dataset` - Path to training dataset (via CLI)

You can provide via config OR CLI:
- `--host` - Remote server address
- `--user` - SSH username
- `--port` - SSH port
- `--learning-rate` - Learning rate
- `--batch-size` - Batch size
- `--epochs` - Number of epochs
- `--warmup-steps` - Warmup steps

## Integration with Improvement Pipeline

After setting up the remote fine-tuner, you can integrate it into the improvement pipeline:

```bash
python scripts/run_improvement_pipeline.py
```

This will:
1. Analyze chat history for patterns
2. Generate training examples from successful interactions
3. Create fine-tuning datasets
4. **Run actual fine-tuning on the GPU server** (via RemoteFineTuner)
5. Generate improvement report

## Troubleshooting

### SSH Connection Failed
```bash
# Check SSH connection manually
ssh -vv mcstar@1.tcp.ngrok.io echo "test"

# Verify SSH key exists
ls -la ~/.ssh/id_rsa

# Check server is reachable
ping 1.tcp.ngrok.io
```

### Dataset Upload Hangs
```bash
# Check disk space on remote server
ssh mcstar@1.tcp.ngrok.io df -h /mnt/12_tb/ollama_data/finetune

# Check if remote directory exists
ssh mcstar@1.tcp.ngrok.io ls -la /mnt/12_tb/ollama_data/finetune
```

### Model Not Found After Fine-tuning
```bash
# List models on remote server
ssh mcstar@1.tcp.ngrok.io ollama list

# Check GPU status
ssh mcstar@1.tcp.ngrok.io nvidia-smi
```

## Next Steps

1. **Verify SSH Works:**
   ```bash
   ssh mcstar@1.tcp.ngrok.io "echo 'SSH connection successful'"
   ```

2. **Create Training Dataset:**
   ```bash
   python scripts/run_improvement_pipeline.py
   # This generates data/training_data.jsonl
   ```

3. **Run Fine-Tuning:**
   ```bash
   python scripts/run_remote_finetuning.py \
     --config config-remote-finetune.json \
     --model qwen2.5-coder:32b \
     --dataset data/training_data.jsonl
   ```

4. **Monitor on Remote Server** (while fine-tuning):
   ```bash
   # In another terminal
   ssh mcstar@1.tcp.ngrok.io "watch -n 1 nvidia-smi"
   ```

## File Locations

- **Config file:** `config-remote-finetune.json`
- **Script:** `scripts/run_remote_finetuning.py`
- **Documentation:** `docs/REMOTE_FINETUNING_GUIDE.md`
- **Configuration fix details:** `docs/REMOTE_FINETUNING_CONFIG_FIX.md`
- **Remote server host:** `1.tcp.ngrok.io`
- **Remote data directory:** `/mnt/12_tb/ollama_data/finetune`
- **Remote models directory:** `/mnt/12_tb/ollama_data/models`

## Contact & Support

For issues:
1. Check `docs/REMOTE_FINETUNING_GUIDE.md` troubleshooting section
2. Review script output logs in `logs/remote_finetune.log`
3. Check remote server logs: `~/.ollama/logs/server.log` (on the GPU server)
