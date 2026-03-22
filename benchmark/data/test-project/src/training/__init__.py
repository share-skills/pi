"""Training module for classical Chinese LLM fine-tuning.

Provides SFT (Supervised Fine-Tuning) and GRPO (Group Relative Policy
Optimization) training with evaluation and configuration management.

Components:
    - trainer: Main training loop with SFT and GRPO support
    - evaluator: Model evaluation with BLEU, ROUGE, and perplexity metrics
    - config_builder: Training configuration management
    - data_loader: Training data loading and preprocessing
"""

from .trainer import Trainer, TrainingConfig
from .evaluator import Evaluator
from .config_builder import ConfigBuilder

__all__ = ["Trainer", "TrainingConfig", "Evaluator", "ConfigBuilder"]
