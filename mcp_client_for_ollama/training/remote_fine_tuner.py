"""Remote Fine-Tuner - Runs actual fine-tuning on GPU servers via SSH"""

import logging
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class RemoteConfig:
    """Configuration for remote GPU server"""
    host: str
    user: str
    port: int = 22
    identity_file: Optional[str] = None  # Path to SSH key
    remote_data_dir: str = "/tmp/ollama_finetune"
    remote_models_dir: str = "~/.ollama/models"


@dataclass
class FineTuningConfig:
    """Configuration for fine-tuning a model"""
    model_name: str
    dataset_path: str  # Local path to JSONL file
    output_model_name: str
    learning_rate: float = 2e-5
    batch_size: int = 16
    num_epochs: int = 3
    warmup_steps: int = 100
    max_steps: Optional[int] = None
    weight_decay: float = 0.01
    save_steps: int = 100


class RemoteFineTuner:
    """
    Manages fine-tuning on remote GPU servers.

    Supports:
    - Fine-tuning Ollama models using ollama fine-tune command
    - Fine-tuning with HuggingFace transformers
    - Fine-tuning with local scripts
    """

    def __init__(self, remote_config: RemoteConfig):
        """
        Initialize remote fine-tuner.

        Args:
            remote_config: Configuration for remote server access
        """
        self.config = remote_config
        self.ssh_available = self._check_ssh()

    def _check_ssh(self) -> bool:
        """Check if SSH is available and configured"""
        try:
            # Test SSH connection (increased timeout for ngrok/slow connections)
            cmd = self._build_ssh_cmd("echo 'SSH connection test'")
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            is_available = result.returncode == 0
            if is_available:
                logger.info(f"SSH connection to {self.config.user}@{self.config.host}:{self.config.port} successful")
            else:
                error = result.stderr.decode() if result.stderr else "Unknown error"
                logger.warning(f"SSH connection to {self.config.user}@{self.config.host}:{self.config.port} failed: {error}")
            return is_available
        except subprocess.TimeoutExpired:
            logger.warning(f"SSH connection timeout to {self.config.user}@{self.config.host}:{self.config.port} (increase timeout if using slow connections)")
            return False
        except Exception as e:
            logger.warning(f"SSH check failed: {e}")
            return False

    def _build_ssh_cmd(self, remote_cmd: str) -> List[str]:
        """Build SSH command

        Uses -q (quiet) and -T (no pseudo-terminal) flags for stability.
        Note: .ssh/config already has port configured for ngrok hosts.
        We rely on that instead of forcing the port, which can cause conflicts.
        """
        cmd = ["ssh", "-q", "-T"]  # Quiet mode and no pseudo-terminal for stability

        # Only add port if explicitly set to non-standard
        # For ngrok connections, .ssh/config handles the port
        # Adding explicit -p can conflict with .ssh/config settings
        if self.config.port and self.config.port != 22 and "ngrok" not in self.config.host:
            cmd.extend(["-p", str(self.config.port)])

        if self.config.identity_file:
            # Expand ~ to home directory
            identity_path = str(Path(self.config.identity_file).expanduser())
            cmd.extend(["-i", identity_path])

        cmd.append(f"{self.config.user}@{self.config.host}")
        cmd.append(remote_cmd)

        return cmd

    def _build_scp_cmd(self, local_path: str, remote_path: str, upload: bool = True) -> List[str]:
        """Build SCP command for file transfer

        Uses -q (quiet) flag for stability.
        Note: .ssh/config can configure ports. For ngrok, let .ssh/config handle it.
        """
        cmd = ["scp", "-q"]  # Quiet mode for stability

        # Only add port if explicitly set to non-standard
        # For ngrok connections, .ssh/config handles the port
        if self.config.port and self.config.port != 22 and "ngrok" not in self.config.host:
            cmd.extend(["-P", str(self.config.port)])

        if self.config.identity_file:
            # Expand ~ to home directory
            identity_path = str(Path(self.config.identity_file).expanduser())
            cmd.extend(["-i", identity_path])

        if upload:
            cmd.append(local_path)
            cmd.append(f"{self.config.user}@{self.config.host}:{remote_path}")
        else:
            cmd.append(f"{self.config.user}@{self.config.host}:{remote_path}")
            cmd.append(local_path)

        return cmd

    def upload_dataset(self, local_path: str, remote_filename: str) -> Tuple[bool, str]:
        """
        Upload training dataset to remote server.

        Args:
            local_path: Local path to JSONL file
            remote_filename: Filename on remote server

        Returns:
            (success, remote_path)
        """
        if not self.ssh_available:
            return False, "SSH not available"

        try:
            local_file = Path(local_path)
            if not local_file.exists():
                return False, f"Local file not found: {local_path}"

            remote_path = f"{self.config.remote_data_dir}/{remote_filename}"

            logger.info(f"Creating remote directory {self.config.remote_data_dir}...")
            mkdir_cmd = self._build_ssh_cmd(f"mkdir -p {self.config.remote_data_dir}")
            result = subprocess.run(mkdir_cmd, capture_output=True, timeout=10)
            if result.returncode != 0:
                error = result.stderr.decode() if result.stderr else "Unknown error"
                logger.warning(f"mkdir warning (may be non-critical): {error}")
                # Don't fail here - directory may already exist or be creatable by SCP

            logger.info(f"Uploading dataset to {remote_path}...")
            scp_cmd = self._build_scp_cmd(local_path, remote_path, upload=True)

            # Retry up to 3 times for transient connection issues
            max_retries = 3
            for attempt in range(max_retries):
                result = subprocess.run(scp_cmd, capture_output=True, timeout=300)

                if result.returncode == 0:
                    logger.info(f"Dataset uploaded successfully")
                    return True, remote_path

                error = result.stderr.decode() if result.stderr else result.stdout.decode()
                if attempt < max_retries - 1:
                    logger.warning(f"Upload attempt {attempt + 1} failed, retrying: {error.strip()}")
                    time.sleep(2)  # Wait before retry
                else:
                    logger.error(f"Upload failed after {max_retries} attempts: {error}")
                    return False, error

        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False, str(e)

    def fine_tune_ollama(self, config: FineTuningConfig) -> Tuple[bool, Dict[str, Any]]:
        """
        Fine-tune a model using Hugging Face Transformers on remote server.

        Note: Ollama does not support fine-tuning. This method:
        1. Creates a fine-tuning script using Hugging Face Transformers
        2. Uploads the script and dataset to remote server
        3. Executes the fine-tuning remotely
        4. The fine-tuned model can then be imported into Ollama

        Args:
            config: Fine-tuning configuration

        Returns:
            (success, result_dict)
        """
        if not self.ssh_available:
            return False, {"error": "SSH not available"}

        try:
            # Upload dataset
            dataset_filename = f"{config.model_name.replace(':', '_')}_dataset.jsonl"
            success, remote_dataset_path = self.upload_dataset(
                config.dataset_path,
                dataset_filename
            )

            if not success:
                return False, {"error": f"Dataset upload failed: {remote_dataset_path}"}

            # Create fine-tuning script
            script_content = self._generate_finetune_script(config, remote_dataset_path)

            # Upload script to remote server
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                local_script_path = f.name

            try:
                remote_script_path = f"{self.config.remote_data_dir}/finetune_script.py"
                scp_cmd = self._build_scp_cmd(local_script_path, remote_script_path, upload=True)
                result = subprocess.run(scp_cmd, capture_output=True, timeout=60)

                if result.returncode != 0:
                    error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                    return False, {"error": f"Script upload failed: {error_msg}"}

                logger.info("Fine-tuning script uploaded successfully")

                # Build and execute the fine-tuning command
                cmd = f"cd {self.config.remote_data_dir} && python3 finetune_script.py"
                logger.info(f"Executing fine-tuning script...")
                ssh_cmd = self._build_ssh_cmd(cmd)

                # Run fine-tuning with progress monitoring
                result = self._run_with_monitoring(ssh_cmd, config.model_name)

                return result

            finally:
                # Clean up temporary local file
                Path(local_script_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Fine-tuning error: {e}")
            return False, {"error": str(e)}

    def _generate_finetune_script(self, config: FineTuningConfig, dataset_path: str) -> str:
        """Generate a fine-tuning Python script using Hugging Face Transformers

        Note: Ollama does not have a built-in fine-tuning feature.
        This generates a Python script that uses Hugging Face Transformers for fine-tuning.
        The fine-tuned model can then be imported into Ollama using a Modelfile.

        Args:
            config: Fine-tuning configuration
            dataset_path: Remote path to JSONL dataset

        Returns:
            Python script content as string
        """
        script = f"""#!/usr/bin/env python3
\"\"\"Fine-tuning script for Ollama models using Hugging Face Transformers\"\"\"

import json
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        BitsAndBytesConfig
    )
    from datasets import Dataset
    import torch
except ImportError as e:
    logger.error(f"Required package missing: {{e}}")
    logger.error("Install with: pip install transformers datasets torch bitsandbytes")
    sys.exit(1)

# Optional: PEFT for LoRA/QLoRA
try:
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    logger.warning("PEFT not available - QLoRA support disabled. Install with: pip install peft")

def load_jsonl_dataset(path):
    \"\"\"Load JSONL dataset\"\"\"
    data = {{"text": []}}
    with open(path, 'r') as f:
        for i, line in enumerate(f):
            try:
                item = json.loads(line)
                # Handle different JSONL formats
                if isinstance(item, dict):
                    if 'text' in item:
                        data['text'].append(item['text'])
                    elif 'content' in item:
                        data['text'].append(item['content'])
                    elif 'prompt' in item and 'completion' in item:
                        data['text'].append(f"{{item['prompt']}}\\n{{item['completion']}}")
                    else:
                        data['text'].append(json.dumps(item))
                else:
                    data['text'].append(str(item))
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON at line {{i+1}}: {{e}}")
    return data

def get_huggingface_model_id(model_name):
    \"\"\"Map Ollama model names to HuggingFace model IDs

    Ollama uses format like 'model:tag', but HuggingFace uses 'org/model-size'
    \"\"\"
    # Remove Ollama tag if present
    base_name = model_name.split(':')[0].lower()

    # Mapping of Ollama models to HuggingFace models
    model_mapping = {{
        'qwen2.5-coder': 'Qwen/Qwen2.5-Coder-7B',
        'qwen2.5-coder-7b': 'Qwen/Qwen2.5-Coder-7B',
        'qwen2.5-coder-14b': 'Qwen/Qwen2.5-Coder-14B',
        'qwen2.5-coder-32b': 'Qwen/Qwen2.5-Coder-32B',
        'llama2': 'meta-llama/Llama-2-7b',
        'llama2-7b': 'meta-llama/Llama-2-7b',
        'llama2-13b': 'meta-llama/Llama-2-13b',
        'llama2-70b': 'meta-llama/Llama-2-70b',
        'mistral': 'mistralai/Mistral-7B',
        'mistral-7b': 'mistralai/Mistral-7B',
        'granite': 'ibm-granite/granite-8b-code-base',
    }}

    if base_name in model_mapping:
        return model_mapping[base_name]
    else:
        return base_name

def main():
    logger.info("Starting fine-tuning job")

    # Configuration
    dataset_path = '{dataset_path}'
    input_model = '{config.model_name}'
    model_id = get_huggingface_model_id(input_model)
    output_dir = './fine-tuned-model'

    logger.info(f"Input model: {{input_model}}")
    logger.info(f"HuggingFace model ID: {{model_id}}")
    logger.info(f"Dataset: {{dataset_path}}")
    logger.info(f"Output: {{output_dir}}")

    # Check if dataset exists
    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {{dataset_path}}")
        sys.exit(1)

    # Load dataset
    logger.info("Loading dataset...")
    data = load_jsonl_dataset(dataset_path)

    if not data['text']:
        logger.error("Dataset is empty")
        sys.exit(1)

    logger.info(f"Loaded {{len(data['text'])}} examples")
    dataset = Dataset.from_dict(data)

    # Split into train/eval
    if len(dataset) > 10:
        split_dataset = dataset.train_test_split(test_size=0.1)
        dataset = {{'train': split_dataset['train'], 'test': split_dataset['test']}}
    else:
        logger.warning("Dataset smaller than 10 examples, using all for training")
        dataset = {{'train': dataset, 'test': dataset}}

    # Load model and tokenizer
    logger.info(f"Loading model {{model_id}}...")
    try:
        # Use QLoRA (4-bit quantization + LoRA) for memory efficiency
        # This works even with batch_size=1 on 24GB GPUs
        use_qlora = PEFT_AVAILABLE and torch.cuda.is_available()

        if use_qlora:
            logger.info("Using QLoRA (4-bit quantization + LoRA) for memory efficiency...")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=bnb_config,
                device_map="auto"
            )
            # Prepare model for training with QLoRA
            model = prepare_model_for_kbit_training(model)

            # Add LoRA adapters
            lora_config = LoraConfig(
                r=64,
                lora_alpha=16,
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                lora_dropout=0.1,
                bias="none",
                task_type="CAUSAL_LM"
            )
            model = get_peft_model(model, lora_config)
            logger.info("✓ QLoRA adapters added")
        else:
            # Fallback: Full precision (will fail on large models with limited memory)
            logger.info("Loading model in full precision (bfloat16)...")
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
                device_map="auto"
            )

        tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Add padding token if needed
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

    except Exception as e:
        logger.error(f"Error loading model {{model_id}}: {{e}}")
        logger.error("Make sure the model ID is available on HuggingFace Hub")
        logger.error("For memory-efficient training, install PEFT:")
        logger.error("  pip install peft")
        logger.error("Full requirements:")
        logger.error("  pip install transformers datasets torch bitsandbytes accelerate peft")
        logger.error("Examples of valid models: 'meta-llama/Llama-2-7b', 'mistralai/Mistral-7B'")
        sys.exit(1)

    # Tokenize dataset
    logger.info("Tokenizing dataset...")
    def tokenize_function(examples):
        tokenized = tokenizer(
            examples['text'],
            truncation=True,
            max_length=512,
            padding='max_length'
        )
        # For causal language modeling, labels are the same as input_ids
        # (predicting the next token)
        tokenized['labels'] = tokenized['input_ids'].copy()
        return tokenized

    # Tokenize both train and test splits
    tokenized_dataset = {{}}
    for split_name, split_data in dataset.items():
        tokenized_dataset[split_name] = split_data.map(
            tokenize_function,
            batched=True,
            remove_columns=['text'],
            desc=f"Tokenizing {{split_name}}"
        )

    # Training arguments with memory optimizations
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate={config.learning_rate},
        per_device_train_batch_size={config.batch_size},
        per_device_eval_batch_size={config.batch_size},
        num_train_epochs={config.num_epochs},
        warmup_steps={config.warmup_steps},
        weight_decay={config.weight_decay},
        save_steps={config.save_steps},
        eval_strategy="steps",
        eval_steps=100 if len(tokenized_dataset['train']) > 100 else len(tokenized_dataset['train']),
        logging_steps=10,
        save_total_limit=2,
        push_to_hub=False,
        bf16=torch.cuda.is_available(),
        fp16=False,  # Use bf16 instead of fp16
        # Memory optimizations
        gradient_checkpointing=True,  # Saves memory during backprop
        gradient_accumulation_steps=8,  # Accumulate gradients over 8 steps
        max_grad_norm=1.0,
        adam_epsilon=1e-6,
    )

    # Enable gradient checkpointing on model
    if hasattr(model, 'gradient_checkpointing_enable'):
        logger.info("Enabling gradient checkpointing...")
        model.gradient_checkpointing_enable()

    # Create trainer
    logger.info("Creating trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset['train'],
        eval_dataset=tokenized_dataset['test'],
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save model
    logger.info(f"Saving fine-tuned model to {{output_dir}}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    logger.info("✓ Fine-tuning complete!")
    logger.info(f"Model saved to {{output_dir}}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Create a Modelfile for Ollama:")
    logger.info(f"   FROM {{output_dir}}")
    logger.info(f"   PARAMETER temperature 0.8")
    logger.info("")
    logger.info("2. Import into Ollama:")
    logger.info(f"   ollama create {config.output_model_name} -f ./Modelfile")
    logger.info("")
    logger.info("3. Run the model:")
    logger.info(f"   ollama run {config.output_model_name}")

if __name__ == "__main__":
    main()
"""
        return script

    def _run_with_monitoring(self, ssh_cmd: List[str], model_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Run command with progress monitoring"""
        try:
            logger.info(f"Executing fine-tuning for {model_name}...")

            # Run the command
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            output_lines = []
            error_lines = []

            # Monitor output
            try:
                stdout, stderr = process.communicate(timeout=3600)  # 1 hour timeout
                output_lines = stdout.split('\n') if stdout else []
                error_lines = stderr.split('\n') if stderr else []
            except subprocess.TimeoutExpired:
                process.kill()
                return False, {"error": "Fine-tuning timeout (1 hour)"}

            success = process.returncode == 0

            result = {
                "model": model_name,
                "success": success,
                "return_code": process.returncode,
                "output_lines": len(output_lines),
                "error_lines": len(error_lines),
                "last_output": output_lines[-5:] if output_lines else [],
                "errors": error_lines[-5:] if error_lines else []
            }

            if success:
                logger.info(f"Fine-tuning completed successfully")
            else:
                logger.error(f"Fine-tuning failed: {error_lines}")

            return success, result

        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            return False, {"error": str(e)}

    def fine_tune_with_script(
        self,
        script_path: str,
        config: FineTuningConfig
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Fine-tune using a custom script on remote server.

        Args:
            script_path: Path to fine-tuning script
            config: Fine-tuning configuration

        Returns:
            (success, result_dict)
        """
        if not self.ssh_available:
            return False, {"error": "SSH not available"}

        try:
            # Upload script
            script_file = Path(script_path)
            if not script_file.exists():
                return False, {"error": f"Script not found: {script_path}"}

            remote_script = f"{self.config.remote_data_dir}/{script_file.name}"

            logger.info(f"Uploading script...")
            scp_cmd = self._build_scp_cmd(script_path, remote_script, upload=True)
            result = subprocess.run(scp_cmd, capture_output=True, timeout=60)

            if result.returncode != 0:
                return False, {"error": "Script upload failed"}

            # Upload dataset
            success, remote_data_path = self.upload_dataset(
                config.dataset_path,
                f"{config.model_name.replace(':', '_')}_dataset.jsonl"
            )

            if not success:
                return False, {"error": f"Dataset upload failed"}

            # Build command to run script
            cmd = f"python {remote_script} --model {config.model_name} --data {remote_data_path}"

            logger.info(f"Running script with fine-tuning...")
            ssh_cmd = self._build_ssh_cmd(cmd)

            return self._run_with_monitoring(ssh_cmd, config.model_name)

        except Exception as e:
            logger.error(f"Script fine-tuning error: {e}")
            return False, {"error": str(e)}

    def get_fine_tuned_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Download fine-tuned model from remote server.

        Args:
            model_name: Name of fine-tuned model on remote server

        Returns:
            (success, local_model_path)
        """
        if not self.ssh_available:
            return False, "SSH not available"

        try:
            # Models are typically stored in ~/.ollama/models/manifests/registry.ollama.ai/
            # For now, just verify it exists on remote
            check_cmd = self._build_ssh_cmd(f"ollama list | grep '{model_name}'")
            result = subprocess.run(check_cmd, capture_output=True)

            if result.returncode == 0:
                logger.info(f"Model {model_name} found on remote server")
                return True, f"remote:{model_name}"
            else:
                return False, "Model not found on remote server"

        except Exception as e:
            logger.error(f"Model check error: {e}")
            return False, str(e)

    def list_remote_models(self) -> Dict[str, Any]:
        """List available models on remote server"""
        if not self.ssh_available:
            return {"error": "SSH not available"}

        try:
            cmd = self._build_ssh_cmd("ollama list")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {"models": result.stdout, "success": True}
            else:
                return {"error": result.stderr, "success": False}

        except Exception as e:
            return {"error": str(e), "success": False}

    def get_remote_status(self) -> Dict[str, Any]:
        """Get status of remote server (GPU usage, disk space, etc.)"""
        if not self.ssh_available:
            return {"connected": False}

        try:
            # Get various system info
            status = {"connected": True}

            # GPU status
            gpu_cmd = self._build_ssh_cmd("nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits")
            result = subprocess.run(gpu_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status["gpu"] = result.stdout.strip()

            # Disk space
            disk_cmd = self._build_ssh_cmd(f"df -h {self.config.remote_data_dir}")
            result = subprocess.run(disk_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status["disk"] = result.stdout.strip()

            # Running processes
            proc_cmd = self._build_ssh_cmd("ps aux | grep -i ollama")
            result = subprocess.run(proc_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                status["processes"] = result.stdout.strip()

            return status

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {"error": str(e), "connected": False}

    def health_check(self) -> Dict[str, Any]:
        """Health check for remote server"""
        return {
            "ssh_available": self.ssh_available,
            "remote_status": self.get_remote_status(),
            "timestamp": time.time()
        }
