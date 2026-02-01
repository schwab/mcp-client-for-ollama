#!/usr/bin/env python3
"""
Remote Fine-Tuning Script

Runs fine-tuning on a remote GPU server via SSH.

Usage:
    python scripts/run_remote_finetuning.py --host 1.tcp.ngroi.io --user mcstar --model qwen2.5-coder:32b --dataset data/training_data.jsonl
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_client_for_ollama.training.remote_fine_tuner import (
    RemoteFineTuner,
    RemoteConfig,
    FineTuningConfig
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = None) -> dict:
    """Load configuration from file"""
    if config_path:
        path = Path(config_path)
    else:
        path = Path.home() / "Nextcloud/DEV/ollmcp/mcp-client-for-ollama/config.remote-finetune.json"

    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    else:
        logger.warning(f"Config file not found: {path}")
        return {}


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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run fine-tuning on remote GPU server",
        epilog="Example: python run_remote_finetuning.py --config config.remote-finetune.json --model qwen2.5-coder:32b --dataset data/training.jsonl"
    )

    # Optional config file
    parser.add_argument('--config', help='Config file path')

    # Server settings (optional if in config)
    parser.add_argument('--host', help='Remote server host')
    parser.add_argument('--user', help='Remote server user')
    parser.add_argument('--port', type=int, help='SSH port')
    parser.add_argument('--identity-file', help='SSH identity file path')

    # Fine-tuning settings (optional if in config)
    parser.add_argument('--model', help='Model to fine-tune')
    parser.add_argument('--output-model', help='Output model name')
    parser.add_argument('--dataset', help='Dataset file path')
    parser.add_argument('--learning-rate', type=float, help='Learning rate')
    parser.add_argument('--batch-size', type=int, help='Batch size')
    parser.add_argument('--epochs', type=int, help='Number of epochs')
    parser.add_argument('--warmup-steps', type=int, help='Warmup steps')
    parser.add_argument('--max-steps', type=int, help='Max training steps')

    # Utilities
    parser.add_argument('--status-only', action='store_true', help='Just check remote status')

    args = parser.parse_args()

    # Load config file if provided
    config = load_config(args.config) if args.config else {}
    config_values = extract_config_values(config)

    # Merge config values with command-line arguments
    # Command-line arguments override config values
    host = args.host or config_values.get('host')
    user = args.user or config_values.get('user')
    port = args.port or config_values.get('port', 22)
    identity_file = args.identity_file or config_values.get('identity_file')
    model = args.model
    output_model = args.output_model
    dataset = args.dataset
    learning_rate = args.learning_rate or config_values.get('learning_rate', 2e-5)
    batch_size = args.batch_size or config_values.get('batch_size', 16)
    epochs = args.epochs or config_values.get('epochs', 3)
    warmup_steps = args.warmup_steps or config_values.get('warmup_steps', 100)
    max_steps = args.max_steps

    # Validate required arguments
    # Server connection and dataset can come from config or CLI
    # Model and dataset must come from CLI (not in config structure)
    missing_args = []
    if not host:
        missing_args.append('--host (or set remote_gpu_server.host in config)')
    if not user:
        missing_args.append('--user (or set remote_gpu_server.user in config)')
    if not model:
        missing_args.append('--model (required, specify via CLI)')
    if not dataset:
        missing_args.append('--dataset (required, specify via CLI)')

    if missing_args:
        parser.error(f"Missing required arguments: {', '.join(missing_args)}")

    # Use model name as output model if not specified
    if not output_model:
        output_model = model

    # Create remote config
    remote_config = RemoteConfig(
        host=host,
        user=user,
        port=port,
        identity_file=identity_file
    )

    # Create fine-tuner
    tuner = RemoteFineTuner(remote_config)

    # Check status if requested
    if args.status_only:
        logger.info("Checking remote server status...")
        status = tuner.health_check()
        print(json.dumps(status, indent=2))
        return 0

    # Verify SSH connection
    if not tuner.ssh_available:
        logger.error("Cannot connect to remote server via SSH")
        return 1

    # Check remote status
    logger.info("Remote server status:")
    status = tuner.get_remote_status()
    print(json.dumps(status, indent=2))

    # Verify dataset exists
    dataset_path = Path(dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset}")
        return 1

    logger.info(f"Dataset size: {dataset_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Create fine-tuning config
    if not output_model:
        output_model = f"{model}_ft"

    ft_config = FineTuningConfig(
        model_name=model,
        dataset_path=dataset,
        output_model_name=output_model,
        learning_rate=learning_rate,
        batch_size=batch_size,
        num_epochs=epochs,
        warmup_steps=warmup_steps,
        max_steps=max_steps
    )

    logger.info(f"Configuration loaded from: {'config file' if args.config else 'defaults and CLI arguments'}")
    if args.config:
        logger.info(f"Config file: {args.config}")

    logger.info(f"Starting fine-tuning job...")
    logger.info(f"  Remote server: {user}@{host}:{port}")
    logger.info(f"  Model: {ft_config.model_name}")
    logger.info(f"  Output: {ft_config.output_model_name}")
    logger.info(f"  Dataset: {dataset}")
    logger.info(f"  Learning rate: {ft_config.learning_rate}")
    logger.info(f"  Batch size: {ft_config.batch_size}")
    logger.info(f"  Epochs: {ft_config.num_epochs}")

    # Run fine-tuning
    success, result = tuner.fine_tune_ollama(ft_config)

    logger.info("Fine-tuning result:")
    print(json.dumps(result, indent=2))

    if success:
        logger.info("✓ Fine-tuning completed successfully")

        # Check if model is available
        logger.info(f"Verifying fine-tuned model...")
        available, location = tuner.get_fine_tuned_model(output_model)

        if available:
            logger.info(f"✓ Model available at: {location}")
        else:
            logger.warning(f"Model {output_model} not found after fine-tuning")

        return 0
    else:
        logger.error("✗ Fine-tuning failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
