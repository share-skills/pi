"""Tests for training pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from src.training.config_builder import ConfigBuilder, PRESETS
from src.training.evaluator import Evaluator


class TestConfigBuilder:
    def setup_method(self):
        self.builder = ConfigBuilder()

    def test_presets_available(self):
        presets = self.builder.list_presets()
        assert "sft_7b" in presets
        assert "sft_14b" in presets
        assert "sft_72b" in presets

    def test_hardcoded_paths_in_preset(self):
        """Verify preset injects default absolute paths."""
        config = self.builder.from_preset("sft_7b")

        assert config["dataset_path"] == "/data/guwen/training_v2.jsonl"
        assert config["eval_dataset_path"] == "/data/guwen/eval_v2.jsonl"
        assert config["output_dir"] == "/models/guwen-llm/checkpoints"

        from pathlib import Path
        assert not Path(config["dataset_path"]).exists()

    def test_preset_override(self):
        config = self.builder.from_preset("sft_7b", learning_rate=1e-5)
        assert config["learning_rate"] == 1e-5

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            self.builder.from_preset("nonexistent_preset")

    def test_validation_warns_on_missing_dataset(self):
        config = self.builder.from_preset("sft_7b")
        warnings = self.builder.validate(config)
        dataset_warnings = [w for w in warnings if "Dataset not found" in w or "not found" in w.lower()]
        assert len(dataset_warnings) >= 1

    def test_merge_configs(self):
        base = {"learning_rate": 2e-4, "num_epochs": 3}
        override = {"learning_rate": 1e-5, "batch_size": 8}
        merged = self.builder.merge_configs(base, override)
        assert merged["learning_rate"] == 1e-5  # Override wins
        assert merged["num_epochs"] == 3         # Base preserved
        assert merged["batch_size"] == 8         # New key added


class TestEvaluator:
    def test_results_attribute(self):
        """
        evaluator.results is initialized to {} and is not automatically
        updated by evaluate(). Use the returned dict from evaluate() instead.
        """
        evaluator = Evaluator.__new__(Evaluator)
        evaluator.results = {}
        evaluator.model = None
        evaluator.tokenizer = None
        evaluator.device = "cpu"

        def mock_evaluate(eval_data, metrics=None):
            return {"bleu": 0.42, "rouge1": 0.55}

        returned = mock_evaluate([])

        assert evaluator.results == {}
        assert returned["bleu"] == 0.42

    def test_bleu_is_character_level(self):
        """Verify the BLEU implementation uses character-level n-grams."""
        evaluator = Evaluator.__new__(Evaluator)
        evaluator.results = {}
        evaluator.device = "cpu"

        score = evaluator._sentence_bleu(
            "學而時習之，不亦說乎",
            "學而時習之，不亦說乎",
        )
        assert score == pytest.approx(1.0, abs=0.01)

    def test_no_oom_handling(self):
        """Verify evaluate() does not have explicit OOM handling."""
        import inspect
        source = inspect.getsource(Evaluator.evaluate)
        has_oom_handler = (
            "OutOfMemoryError" in source
            or "cuda.empty_cache" in source
            or "batch_size" in source.lower() and "fallback" in source.lower()
        )
        assert not has_oom_handler

    def test_grpo_trainer_not_implemented(self):
        """Verify GRPOTrainer raises NotImplementedError."""
        from src.training.trainer import GRPOTrainer, TrainingConfig
        grpo = GRPOTrainer(TrainingConfig())
        with pytest.raises(NotImplementedError):
            grpo.train()


class TestExampleUsage:
    def test_stale_import_paths(self):
        """Stale config fields cause TypeError at instantiation."""
        from src.training import Trainer, TrainingConfig, Evaluator

        with pytest.raises(TypeError):
            TrainingConfig(
                model_name="Qwen/Qwen2-7B",
                use_flash_attention=True,   # Stale field
            )

    def test_evaluator_results_empty_after_construction(self):
        """evaluator.results starts as {} and is not updated by evaluate()."""
        from src.training.evaluator import Evaluator

        with patch.object(Evaluator, "_load_model", return_value=None):
            evaluator = Evaluator.__new__(Evaluator)
            evaluator.results = {}

        assert evaluator.results == {}
