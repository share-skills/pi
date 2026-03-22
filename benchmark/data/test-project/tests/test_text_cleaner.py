"""Tests for text cleaner module."""

import pytest
import time
from src.data_processing.text_cleaner import TextCleaner, CleanerConfig, TextNormalizer


class TestTextCleaner:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_basic_clean(self):
        text = "子曰：學而時習之，不亦說乎？"
        result = self.cleaner.clean(text)
        assert "子曰" in result
        assert len(result) > 0

    def test_empty_input(self):
        assert self.cleaner.clean("") == ""
        assert self.cleaner.clean("   ") == ""

    def test_unicode_normalization(self):
        # BOM and zero-width spaces should be removed
        text = "\ufeff子曰\u200b學而"
        result = self.cleaner.clean(text)
        assert "\ufeff" not in result
        assert "\u200b" not in result

    def test_ocr_correction(self):
        # 爲 → 為 correction
        text = "天下爲公"
        result = self.cleaner.clean(text)
        assert "為" in result

    def test_punct_patterns_defined(self):
        """Verify that punct_patterns attribute is present on the cleaner."""
        cleaner = TextCleaner()
        assert hasattr(cleaner, "punct_patterns")
        assert "period" in cleaner.punct_patterns
        assert "comma" in cleaner.punct_patterns

    def test_whitespace_collapse(self):
        """Verify whitespace normalisation behaviour."""
        # Text with a double newline (paragraph break)
        text = "第一段落。\n\n第二段落。"
        result = self.cleaner.clean(text)
        # Double newlines are collapsed to single newlines
        assert "\n\n" not in result
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 2

    def test_exact_dedup(self):
        """Verify exact-match dedup removes repeated sentences."""
        text = "學而時習之。學而時習之。學而時習之。"
        result = self.cleaner.clean(text)
        count = result.count("學而時習之")
        assert count < 3

        # Near-duplicates (differ by one char) are not caught by exact match
        text2 = "學而時習之。學而時習之 。"  # Trailing space differs
        result2 = TextCleaner().clean(text2)
        # Both may survive since they differ slightly

    def test_recover_punctuation_performance(self):
        """Verify cleaning completes in reasonable time on moderate input."""
        cleaner = TextCleaner()
        text = "天下大同" * 500 + "\n" + "天下大同" * 500
        start = time.time()
        result = cleaner.clean(text)
        elapsed = time.time() - start
        assert elapsed < 30, f"Cleaning took {elapsed:.1f}s — possible performance issue"

    def test_stats_tracking(self):
        cleaner = TextCleaner()
        cleaner.clean("子曰學而時習之")
        stats = cleaner.get_stats()
        assert stats["chars_processed"] > 0

    def test_clean_batch(self):
        cleaner = TextCleaner()
        texts = ["子曰學而時習之", "有朋自遠方來", ""]
        results = cleaner.clean_batch(texts)
        assert len(results) == 3
        assert results[2] == ""


class TestTextNormalizer:
    def test_variant_unification(self):
        text = "峯巒疊嶂，羣山環抱"
        result = TextNormalizer.unify_variants(text)
        assert "峰" in result
        assert "群" in result
        assert "峯" not in result

    def test_chinese_char_count(self):
        text = "子曰 hello 123"
        count = TextNormalizer.count_chinese_chars(text)
        assert count == 2  # 子, 曰

    def test_chinese_ratio(self):
        text = "天地玄黃"
        ratio = TextNormalizer.chinese_ratio(text)
        assert ratio == 1.0

        mixed = "hello世界"
        ratio2 = TextNormalizer.chinese_ratio(mixed)
        assert 0 < ratio2 < 1

    def test_empty_ratio(self):
        assert TextNormalizer.chinese_ratio("") == 0.0
