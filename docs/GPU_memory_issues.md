Yes, you can use both GPUs more efficiently! The error suggests you're **not fully utilizing both GPUs** - most memory is on GPU 0, while GPU 1 might be underutilized. Here are solutions:

## **1. Enable Proper Multi-GPU Training**

### **Using Fully Sharded Data Parallel (FSDP)** - **Best for your setup**
FSDP shards model parameters, gradients, and optimizer states across GPUs:

```yaml
# In your Axolotl config (axolotl.yml)
fsdp: "full_shard auto_wrap"
fsdp_config:
  fsdp_transformer_layer_cls_to_wrap: LlamaDecoderLayer  # Adjust based on model
  xla: false
  xla_fsdp_v2: false
  xla_fsdp_grad_ckpt: false
```

Or in Python:
```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP

model = FSDP(
    model,
    auto_wrap_policy=transformer_auto_wrap_policy,
    # ... other FSDP settings
)
```

### **Using DeepSpeed** (especially ZeRO-3)
Add a `deepspeed_config.json`:
```json
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {"device": "cpu"},
    "offload_param": {"device": "cpu"}
  },
  "train_micro_batch_size_per_gpu": 1,
  "gradient_accumulation_steps": 8
}
```
Run with: `deepspeed --num_gpus=2 train.py`

## **2. Optimize Your Training Configuration**

### **Reduce Memory Usage:**
```yaml
# In axolotl.yml
micro_batch_size: 1  # As low as possible
gradient_accumulation_steps: 8  # Increase to maintain effective batch size
gradient_checkpointing: true  # Saves memory, slower but essential
bf16: true  # Better than fp16 for memory
tf32: false  # Disable if not needed

# LoRA settings (if using LoRA)
adapter: lora
lora_r: 8
lora_alpha: 16
lora_dropout: 0.05
lora_target_linear: true
```

### **QLoRA Configuration** (Most memory efficient):
```yaml
load_in_4bit: true  # Load model in 4-bit
bnb_4bit_quant_type: nf4
bnb_4bit_compute_dtype: bfloat16
adapter: qlora
lora_r: 64
lora_alpha: 16
lora_dropout: 0.1
```

## **3. Command Line Solutions**

### **Set Environment Variables:**
```bash
# Prevent memory fragmentation
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CUDA_LAUNCH_BLOCKING=1

# Clear cache before running
export PYTHONPATH=""

# For PyTorch 2.0+
export TORCHDYNAMO_DISABLE=1
```

### **Use Accelerate with FSDP:**
```bash
accelerate config  # Configure for multi-GPU
accelerate launch --num_processes=2 train.py
```

## **4. Immediate Fixes for Your Current Error**

### **A. Check GPU Memory Distribution:**
```python
import torch
print(f"GPU 0 memory: {torch.cuda.memory_allocated(0)/1e9:.2f}GB")
print(f"GPU 1 memory: {torch.cuda.memory_allocated(1)/1e9:.2f}GB")
```

### **B. Force Data Parallel with Explicit Device Placement:**
```python
# If using simple DataParallel (not as efficient as FSDP but works)
model = torch.nn.DataParallel(model, device_ids=[0, 1])
model = model.to('cuda:0')  # Primary GPU
```

## **5. Recommended Axolotl Config for 14B on 2x24GB:**

```yaml
# axolotl.yml
base_model: meta-llama/Llama-2-13b-hf  # or your 14B model
model_type: LlamaForCausalLM

# Memory optimization
load_in_8bit: false  # Set to true if not using LoRA
load_in_4bit: true   # For QLoRA
bf16: true
fp16: false
tf32: false

# LoRA/QLoRA
adapter: qlora
lora_r: 64
lora_alpha: 16
lora_dropout: 0.1
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

# Training
micro_batch_size: 1
gradient_accumulation_steps: 16
num_epochs: 3
learning_rate: 2e-4
optimizer: paged_adamw_8bit

# Memory saving
gradient_checkpointing: true
group_by_length: true
packing: false

# Multi-GPU
fsdp: "full_shard auto_wrap"
fsdp_config:
  min_num_params: 2000
  fsdp_transformer_layer_cls_to_wrap: LlamaDecoderLayer
```

## **6. Quick Test to Verify GPU Usage:**
```bash
# Monitor GPU usage during training
watch -n 1 nvidia-smi

# Or use PyTorch to check
python -c "import torch; print(f'GPUs: {torch.cuda.device_count()}, Memory: {[torch.cuda.get_device_properties(i).total_memory/1e9 for i in range(torch.cuda.device_count())]}')"
```

## **7. If Still Failing: Consider Offloading**

```python
# CPU offloading as last resort
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

with init_empty_weights():
    model = AutoModelForCausalLM.from_pretrained("your-model")

model = load_checkpoint_and_dispatch(
    model, 
    checkpoint="your-model",
    device_map="auto",
    offload_folder="offload",
    no_split_module_classes=["LlamaDecoderLayer"]
)
```

**Most Likely Fix**: Use **QLoRA + FSDP** with `micro_batch_size: 1` and `gradient_accumulation_steps: 8-16`. This should fit a 14B model on 2x24GB GPUs.

Would you like me to help you modify your specific training script or Axolotl config?