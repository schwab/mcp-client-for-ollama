# Remote Fine-Tuning Config File Fix

## Issue
The remote fine-tuning script allowed specification of a config file with `--config`, but still required `--host`, `--user`, `--model`, and `--dataset` as mandatory CLI arguments, making the config file effectively useless.

## Solution
Updated `scripts/run_remote_finetuning.py` to properly merge configuration file values with CLI arguments:

### Changed Behavior

**Before:**
```bash
# Required ALL arguments regardless of config file
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

**After:**
```bash
# Config file provides server and fine-tuning defaults
# Only model and dataset required from CLI
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

### What Moved to Config File

The following settings can now be loaded from the config file (`config.remote-finetune.json`):

**Server Connection Settings:**
- `host` - Remote server hostname/IP
- `user` - SSH username
- `port` - SSH port (defaults to 22)
- `identity_file` - Path to SSH private key

**Fine-Tuning Defaults:**
- `learning_rate` - Learning rate for training
- `batch_size` - Batch size for training
- `num_epochs` - Number of training epochs
- `warmup_steps` - Warmup steps for scheduler

### What Remains CLI-Only

These MUST be specified via command-line arguments:
- `--model` - Which model to fine-tune
- `--dataset` - Path to training dataset

This makes sense because:
1. The config structure supports multiple models with model-specific settings, not a single default model
2. Dataset paths vary per training run
3. These are typically specific to each fine-tuning job, not server-wide defaults

### Implementation Details

**1. Updated `extract_config_values()` function:**
```python
def extract_config_values(config: dict) -> dict:
    """Extract relevant config values for command-line defaults"""
    extracted = {}

    # Extract remote server settings
    if 'remote_gpu_server' in config:
        server = config['remote_gpu_server']
        extracted['host'] = server.get('host')
        extracted['user'] = server.get('user')
        extracted['port'] = server.get('port', 22)
        extracted['identity_file'] = server.get('identity_file')

    # Extract fine-tuning defaults
    if 'fine_tuning' in config:
        ft = config['fine_tuning']
        defaults = ft.get('defaults', {})
        extracted['learning_rate'] = defaults.get('learning_rate', 2e-5)
        extracted['batch_size'] = defaults.get('batch_size', 16)
        extracted['epochs'] = defaults.get('num_epochs', 3)
        extracted['warmup_steps'] = defaults.get('warmup_steps', 100)

    return extracted
```

**2. Updated argument merging logic:**
```python
# Merge config values with command-line arguments
# Command-line arguments override config values
host = args.host or config_values.get('host')
user = args.user or config_values.get('user')
port = args.port or config_values.get('port', 22)
identity_file = args.identity_file or config_values.get('identity_file')
model = args.model  # Must come from CLI
dataset = args.dataset  # Must come from CLI
learning_rate = args.learning_rate or config_values.get('learning_rate', 2e-5)
batch_size = args.batch_size or config_values.get('batch_size', 16)
epochs = args.epochs or config_values.get('epochs', 3)
warmup_steps = args.warmup_steps or config_values.get('warmup_steps', 100)
```

**3. Updated validation messages:**
```python
# Clear messages about which arguments come from where
if not host:
    missing_args.append('--host (or set remote_gpu_server.host in config)')
if not user:
    missing_args.append('--user (or set remote_gpu_server.user in config)')
if not model:
    missing_args.append('--model (required, specify via CLI)')
if not dataset:
    missing_args.append('--dataset (required, specify via CLI)')
```

## Usage Examples

### Minimal - Config provides everything except model and dataset:
```bash
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

### Override config defaults with CLI:
```bash
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --learning-rate 0.00005 \
  --epochs 5
```

### No config file - all CLI:
```bash
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```

### Status check with config:
```bash
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model dummy \
  --dataset dummy.jsonl \
  --status-only
```

## Precedence Rules

When the same parameter is specified in both config and CLI:
1. **CLI argument takes precedence** over config file value
2. **Config file value** is used if CLI argument not provided
3. **Built-in defaults** are used if neither provided

Example:
```bash
# Config has learning_rate: 0.00002
# CLI specifies --learning-rate 0.00005
# Result: 0.00005 (CLI wins)
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --learning-rate 0.00005
```

## Configuration File Structure

Minimal required config:
```json
{
  "remote_gpu_server": {
    "host": "1.tcp.ngroi.io",
    "user": "mcstar"
  },
  "fine_tuning": {
    "defaults": {
      "learning_rate": 0.00002,
      "batch_size": 16,
      "num_epochs": 3
    }
  }
}
```

See `config.remote-finetune.example.json` for full structure with all options.

## Testing

To verify the fix works:

```bash
# Should fail with clear error messages
python scripts/run_remote_finetuning.py --config config.remote-finetune.json
# Output: Missing required arguments: --model (required, specify via CLI), --dataset (required, specify via CLI)

# Should load config and proceed
python scripts/run_remote_finetuning.py \
  --config config.remote-finetune.json \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl \
  --status-only
# Output: Shows remote server status (if SSH works)
```

## Files Modified

- `scripts/run_remote_finetuning.py`
  - Updated `extract_config_values()` function
  - Updated argument merging logic in `main()`
  - Updated validation error messages
  - All arguments now optional (not required=True)

## Backward Compatibility

The change is fully backward compatible. Existing usage with all CLI arguments continues to work:

```bash
# Old way - still works
python scripts/run_remote_finetuning.py \
  --host 1.tcp.ngroi.io \
  --user mcstar \
  --model qwen2.5-coder:32b \
  --dataset data/training_data.jsonl
```
