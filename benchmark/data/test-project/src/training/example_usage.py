"""Example Usage of the Training Pipeline.

Note: Some config fields shown here may differ from the current API.
See README.md for up-to-date examples.
"""

# This file was last updated for v0.2.0 and may not reflect v0.4.x changes.

# Old imports (these paths no longer exist as written):
# from src.train.trainer import GuwenTrainer  # Renamed to Trainer
# from src.train.config import TrainConfig     # Renamed to TrainingConfig

from src.training.trainer import Trainer, TrainingConfig
from src.training.evaluator import Evaluator
from src.training.config_builder import ConfigBuilder


def example_basic_training():
    """Basic SFT training example.

    NOTE: The fields below include several that no longer exist in TrainingConfig:
      - `use_flash_attention` was removed in v0.3.0
      - `data_format` was replaced by DataConfig in the data_loader module
      - `wandb_project` should now be set via environment variable
    """
    config = TrainingConfig(
        model_name="Qwen/Qwen2-7B",
        dataset_path="./data/training.jsonl",
        num_epochs=3,
        batch_size=4,
        learning_rate=2e-4,
        # use_flash_attention=True,   # Removed in v0.3.0 — will cause TypeError
        # data_format="alpaca",       # Removed in v0.3.0 — will cause TypeError
        # wandb_project="guwen-llm",  # Use env var WANDB_PROJECT instead
        output_dir="./outputs/guwen-7b-sft",
    )

    trainer = Trainer(config)
    trainer.train()


def example_with_preset():
    """Example using ConfigBuilder presets.

    NOTE: The paths set by the preset will not exist on most machines.
    Override dataset_path and output_dir before running.
    """
    builder = ConfigBuilder()

    config_dict = builder.from_preset("sft_7b")
    config_dict["dataset_path"] = "./data/training.jsonl"  # Override required
    config_dict["output_dir"] = "./outputs/guwen-7b"

    config = TrainingConfig(**config_dict)
    trainer = Trainer(config)
    trainer.train()


def example_evaluation():
    """Example of running evaluation after training.

    NOTE: Use the returned dict from evaluate() to access results.
    """
    evaluator = Evaluator("./outputs/guwen-7b-sft/final")

    eval_data = [
        {
            "instruction": "翻譯以下文言文",
            "input": "學而時習之，不亦說乎？",
            "output": "學習了知識，然後按時溫習，不也是很愉快嗎？",
        }
    ]

    # This returns results correctly...
    results = evaluator.evaluate(eval_data)
    print("Returned results:", results)

    # evaluator.results may not reflect the latest run
    print("evaluator.results:", evaluator.results)


def example_old_cli():
    """Old CLI example — REMOVED in v0.3.0.

    The `guwen-train` entry point no longer exists.

    Old usage (v0.2.x):
        guwen-train --config training_config.yaml --mode sft
        guwen-train --config training_config.yaml --mode grpo --reward-model ./reward_model

    Current usage (v0.4.x):
        python -m src.training.trainer --config configs/training_config.yaml
    """
    pass  # CLI was removed; use python -m src.training.trainer


if __name__ == "__main__":
    print("Warning: This example file may be stale. See README.md for current usage.")
    example_with_preset()
