"""Configuration Builder for Training Pipelines.

Provides utilities for building, validating, and managing training
configurations. Supports presets for common training scenarios and
environment-specific overrides.

Usage:
    builder = ConfigBuilder()
    config = builder.from_preset("sft_7b")
    config = builder.override(config, learning_rate=1e-5)
"""

import os
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from copy import deepcopy

import yaml

logger = logging.getLogger(__name__)


# ─── Training Presets ─────────────────────────────────────────────────────────

PRESETS = {
    "sft_7b": {
        "model_name": "Qwen/Qwen2-7B",
        "lora_r": 64,
        "lora_alpha": 128,
        "batch_size": 4,
        "gradient_accumulation_steps": 4,
        "learning_rate": 2e-4,
        "num_epochs": 3,
        "max_seq_length": 2048,
        "quantization": "4bit",
        "bf16": True,
    },
    "sft_14b": {
        "model_name": "Qwen/Qwen2-14B",
        "lora_r": 32,
        "lora_alpha": 64,
        "batch_size": 2,
        "gradient_accumulation_steps": 8,
        "learning_rate": 1e-4,
        "num_epochs": 2,
        "max_seq_length": 2048,
        "quantization": "4bit",
        "bf16": True,
    },
    "sft_72b": {
        "model_name": "Qwen/Qwen2-72B",
        "lora_r": 16,
        "lora_alpha": 32,
        "batch_size": 1,
        "gradient_accumulation_steps": 16,
        "learning_rate": 5e-5,
        "num_epochs": 1,
        "max_seq_length": 1024,
        "quantization": "4bit",
        "bf16": True,
    },
}


class ConfigBuilder:
    """Builds and manages training configurations.

    Provides methods for creating configs from presets, loading from
    files, and applying overrides.

    Example:
        >>> builder = ConfigBuilder()
        >>> config = builder.from_preset("sft_7b")
        >>> config = builder.override(config, num_epochs=5)
        >>> builder.save(config, "my_config.yaml")
    """

    def __init__(self):
        self._presets = deepcopy(PRESETS)

    def from_preset(self, preset_name: str, **overrides) -> Dict[str, Any]:
        """Create a config from a named preset.

        Args:
            preset_name: Name of the preset (sft_7b, sft_14b, sft_72b).
            **overrides: Key-value pairs to override preset values.

        Returns:
            Configuration dictionary.
        """
        if preset_name not in self._presets:
            available = ", ".join(self._presets.keys())
            raise ValueError(
                f"Unknown preset '{preset_name}'. Available: {available}"
            )

        config = deepcopy(self._presets[preset_name])

        config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
        config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
        config.setdefault("output_dir", "/models/guwen-llm/checkpoints")

        # Apply overrides
        config.update(overrides)

        return config

    def from_file(self, config_path: str) -> Dict[str, Any]:
        """Load config from a YAML file.

        Args:
            config_path: Path to YAML config file.

        Returns:
            Configuration dictionary.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config.get("training", config)

    def override(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Apply overrides to an existing config.

        Args:
            config: Base configuration dict.
            **kwargs: Key-value pairs to override.

        Returns:
            New config dict with overrides applied.
        """
        new_config = deepcopy(config)
        new_config.update(kwargs)
        return new_config

    def save(self, config: Dict[str, Any], output_path: str):
        """Save config to a YAML file.

        Args:
            config: Configuration dict to save.
            output_path: Path for the output YAML file.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            yaml.dump(
                {"training": config},
                f,
                default_flow_style=False,
                allow_unicode=True,
            )

        logger.info(f"Config saved to {output_path}")

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate a configuration and return warnings.

        Args:
            config: Configuration dict to validate.

        Returns:
            List of warning/error messages.
        """
        warnings = []

        # Check required fields
        required = ["model_name", "dataset_path", "output_dir"]
        for field_name in required:
            if field_name not in config:
                warnings.append(f"Missing required field: {field_name}")

        # Check dataset exists
        dataset_path = config.get("dataset_path", "")
        if dataset_path and not Path(dataset_path).exists():
            warnings.append(f"Dataset not found: {dataset_path}")

        # Check output dir is writable
        output_dir = config.get("output_dir", "")
        if output_dir:
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            except PermissionError:
                warnings.append(f"Cannot write to output dir: {output_dir}")

        # Check GPU availability for bf16
        if config.get("bf16", False):
            try:
                import torch
                if not torch.cuda.is_available():
                    warnings.append("bf16 requested but CUDA is not available")
                elif not torch.cuda.is_bf16_supported():
                    warnings.append("bf16 requested but GPU does not support bf16")
            except ImportError:
                warnings.append("torch not installed, cannot verify GPU")

        # Check learning rate range
        lr = config.get("learning_rate", 0)
        if lr > 1e-3:
            warnings.append(f"Learning rate {lr} seems too high for fine-tuning")
        if lr < 1e-6:
            warnings.append(f"Learning rate {lr} seems too low")

        return warnings

    def list_presets(self) -> Dict[str, Dict]:
        """List all available presets."""
        return deepcopy(self._presets)

    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configs, with later configs taking precedence."""
        merged = {}
        for config in configs:
            merged.update(config)
        return merged
