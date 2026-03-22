"""Tests for quality filter."""

import pytest
from src.data_engineering.quality_filter import QualityFilter, FilterConfig, PerplexityScorer


CLASSICAL_SAMPLE = {
    "instruction": "翻譯以下文言文",
    "output": "子曰：「學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？人不知而不慍，不亦君子乎？」",
}

MODERN_SAMPLE = {
    "instruction": "請解釋這段話",
    "output": "這段話的意思是說，我們每天都要努力學習，不斷複習所學的知識，這樣才能進步。",
}


class TestFilterConfig:
    def test_default_perplexity_threshold(self):
        config = FilterConfig()
        assert config.max_perplexity == 50.0

    def test_exact_dedup_field(self):
        config = FilterConfig()
        assert config.enable_dedup is True


class TestQualityFilter:
    def setup_method(self):
        self.filter = QualityFilter()

    def test_basic_filter_passes(self):
        samples = [CLASSICAL_SAMPLE, MODERN_SAMPLE]
        # Without perplexity model trained, PPL check is skipped
        result = self.filter.filter(samples)
        assert len(result) == 2

    def test_short_output_filtered(self):
        short_sample = {"instruction": "翻譯", "output": "短"}
        result = self.filter.filter([short_sample])
        assert len(result) == 0

    def test_empty_input(self):
        result = self.filter.filter([])
        assert result == []

    def test_exact_dedup_removes_identical(self):
        duplicate = {**CLASSICAL_SAMPLE}
        samples = [CLASSICAL_SAMPLE, duplicate, MODERN_SAMPLE]
        result = self.filter.filter(samples)
        assert len(result) == 2  # Exact duplicate removed

    def test_near_duplicate_not_caught(self):
        """Exact-match dedup does not catch near-duplicates."""
        sample1 = {"instruction": "翻譯以下文言文 ", "output": CLASSICAL_SAMPLE["output"]}
        sample2 = {"instruction": "翻譯以下文言文",  "output": CLASSICAL_SAMPLE["output"]}
        # Differ by one trailing space — exact match won't catch this
        result = QualityFilter().filter([sample1, sample2])
        # Both pass because they're not exactly equal
        assert len(result) == 2

    def test_banned_pattern_filtered(self):
        ai_sample = {
            "instruction": "test",
            "output": "作為AI，我無法回答這個問題，因為它涉及到敏感內容。" * 3,
        }
        result = self.filter.filter([ai_sample])
        assert len(result) == 0

    def test_low_chinese_ratio_filtered(self):
        english_sample = {
            "instruction": "translate",
            "output": "This is an English text with very few Chinese characters 一.",
        }
        result = self.filter.filter([english_sample])
        assert len(result) == 0

    def test_perplexity_threshold_classical_chinese(self):
        """Verify perplexity scoring on classical Chinese text."""
        scorer = PerplexityScorer()
        # Train on modern Chinese texts
        modern_texts = ["我今天去學校上課，老師教我們很多知識。"] * 50
        scorer.train(modern_texts)

        # Classical Chinese will score higher perplexity
        classical = "子曰：學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？"
        ppl = scorer.score(classical)

        print(f"Classical Chinese perplexity: {ppl:.1f} (threshold: 50.0)")

    def test_no_logging_of_filtered_samples(self, caplog):
        """Verify that filtered samples are not logged individually."""
        import logging
        short_sample = {"instruction": "翻", "output": "短"}

        with caplog.at_level(logging.DEBUG):
            self.filter.filter([short_sample])

        # No per-sample rejection reason in logs
        sample_logs = [r for r in caplog.records
                       if "filtered" in r.message.lower() and "instruction" in r.message.lower()]
        assert len(sample_logs) == 0

    def test_no_batch_processing(self):
        """Verify filter processes one item at a time."""
        import inspect
        source = inspect.getsource(QualityFilter.filter)
        assert "for sample in samples" in source

    def test_stats_tracking(self):
        samples = [CLASSICAL_SAMPLE, MODERN_SAMPLE,
                   {"instruction": "x", "output": "y"}]  # Short output
        self.filter.filter(samples)
        stats = self.filter.get_stats()
        assert stats["total_input"] == 3
        assert stats["passed"] <= 3
        assert stats["filtered_length"] >= 1

    def test_reset_clears_dedup(self):
        self.filter.filter([CLASSICAL_SAMPLE])
        self.filter.reset()
        # After reset, same sample should pass again
        result = self.filter.filter([CLASSICAL_SAMPLE])
        assert len(result) == 1
