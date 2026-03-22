"""Quality Filter for Training Data.

Filters and validates training data for quality before use in model training.
Applies multiple quality checks including perplexity scoring, deduplication,
language detection, and content validation.

Usage:
    qf = QualityFilter(config)
    filtered = qf.filter(samples)
    print(f"Kept {len(filtered)}/{len(samples)} samples")
"""

import re
import math
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for quality filtering."""
    # Perplexity filtering
    max_perplexity: float = 50.0

    # Length filtering
    min_length: int = 20
    max_length: int = 4096
    min_instruction_length: int = 5
    min_output_length: int = 20

    # Content filtering
    min_chinese_ratio: float = 0.3
    max_repetition_ratio: float = 0.3
    banned_patterns: List[str] = field(default_factory=lambda: [
        r"(?i)as an ai",
        r"(?i)i cannot",
        r"(?i)i'm sorry",
        r"抱歉.*我無法",
        r"作為AI",
    ])

    # Dedup settings
    enable_dedup: bool = True
    dedup_field: str = "instruction"


class PerplexityScorer:
    """Estimates perplexity for Chinese text using character-level n-grams.

    Uses a simple character bigram model trained on a reference corpus
    to estimate how "surprising" a text is. Higher perplexity = more
    unusual text patterns.

    Note: This is a rough heuristic, not a true language model perplexity.
    """

    def __init__(self):
        self._bigram_probs: Dict[str, float] = {}
        self._unigram_probs: Dict[str, float] = {}
        self._trained = False

    def train(self, reference_texts: List[str]):
        """Train the n-gram model on reference texts."""
        bigram_counts = Counter()
        unigram_counts = Counter()
        total_chars = 0

        for text in reference_texts:
            chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
            for c in chars:
                unigram_counts[c] += 1
                total_chars += 1
            for i in range(len(chars) - 1):
                bigram_counts[chars[i] + chars[i + 1]] += 1

        # Compute probabilities with Laplace smoothing
        vocab_size = len(unigram_counts)
        for bigram, count in bigram_counts.items():
            first_char = bigram[0]
            self._bigram_probs[bigram] = (
                (count + 1) / (unigram_counts[first_char] + vocab_size)
            )

        for char, count in unigram_counts.items():
            self._unigram_probs[char] = count / total_chars

        self._trained = True

    def score(self, text: str) -> float:
        """Compute perplexity score for a text.

        Returns:
            Perplexity score (lower = more typical).
        """
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if len(chars) < 2:
            return float("inf")

        log_prob_sum = 0.0
        n = 0

        for i in range(len(chars) - 1):
            bigram = chars[i] + chars[i + 1]
            prob = self._bigram_probs.get(bigram, 1e-6)
            log_prob_sum += math.log2(prob)
            n += 1

        if n == 0:
            return float("inf")

        avg_log_prob = log_prob_sum / n
        perplexity = 2 ** (-avg_log_prob)

        return perplexity


class QualityFilter:
    """Filters training data for quality.

    Applies multiple quality checks to ensure training data meets
    minimum standards for model training.

    Args:
        config: FilterConfig with filtering thresholds.

    Example:
        >>> qf = QualityFilter()
        >>> samples = [{"instruction": "翻譯此文", "output": "..."}]
        >>> filtered = qf.filter(samples)
    """

    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()
        self._scorer = PerplexityScorer()
        self._seen_hashes: Set[str] = set()  # For dedup
        self._compiled_patterns = [
            re.compile(p) for p in self.config.banned_patterns
        ]
        self._stats = {
            "total_input": 0,
            "passed": 0,
            "filtered_length": 0,
            "filtered_perplexity": 0,
            "filtered_content": 0,
            "filtered_dedup": 0,
            "filtered_language": 0,
        }

    def filter(self, samples: List[Dict]) -> List[Dict]:
        """Filter a list of training samples.

        Args:
            samples: List of sample dicts with 'instruction' and 'output' keys.

        Returns:
            Filtered list of samples that pass all quality checks.
        """
        self._stats["total_input"] = len(samples)
        filtered = []

        for sample in samples:
            if self._passes_all_checks(sample):
                filtered.append(sample)
                self._stats["passed"] += 1

        logger.info(
            f"Quality filter: {self._stats['passed']}/{self._stats['total_input']} "
            f"samples passed"
        )

        return filtered

    def _passes_all_checks(self, sample: Dict) -> bool:
        """Run all quality checks on a sample."""
        # Length check
        if not self._check_length(sample):
            self._stats["filtered_length"] += 1
            return False

        # Language check
        if not self._check_language(sample):
            self._stats["filtered_language"] += 1
            return False

        # Content check
        if not self._check_content(sample):
            self._stats["filtered_content"] += 1
            return False

        # Perplexity check
        if self._scorer._trained and not self._check_perplexity(sample):
            self._stats["filtered_perplexity"] += 1
            return False

        # Dedup check
        if self.config.enable_dedup and not self._check_dedup(sample):
            self._stats["filtered_dedup"] += 1
            return False

        return True

    def _check_length(self, sample: Dict) -> bool:
        """Check if sample meets length requirements."""
        instruction = sample.get("instruction", "")
        output = sample.get("output", "")

        if len(instruction) < self.config.min_instruction_length:
            return False
        if len(output) < self.config.min_output_length:
            return False

        total = len(instruction) + len(output)
        if total < self.config.min_length or total > self.config.max_length:
            return False

        return True

    def _check_language(self, sample: Dict) -> bool:
        """Check if sample has sufficient Chinese content."""
        text = sample.get("output", "") + sample.get("instruction", "")
        if not text:
            return False

        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        if total_chars == 0:
            return False

        ratio = chinese_chars / total_chars
        return ratio >= self.config.min_chinese_ratio

    def _check_content(self, sample: Dict) -> bool:
        """Check for banned patterns and excessive repetition."""
        text = sample.get("output", "")

        # Check banned patterns
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return False

        # Check repetition
        if self._repetition_ratio(text) > self.config.max_repetition_ratio:
            return False

        return True

    def _check_perplexity(self, sample: Dict) -> bool:
        """Check if sample's perplexity is within threshold."""
        text = sample.get("output", "")
        score = self._scorer.score(text)
        return score <= self.config.max_perplexity

    def _check_dedup(self, sample: Dict) -> bool:
        """Check for duplicate samples."""
        dedup_text = sample.get(self.config.dedup_field, "")
        text_hash = dedup_text.strip()  # Just using the text as-is

        if text_hash in self._seen_hashes:
            return False

        self._seen_hashes.add(text_hash)
        return True

    def _repetition_ratio(self, text: str) -> float:
        """Calculate the ratio of repeated n-grams in text."""
        if len(text) < 10:
            return 0.0

        # Use 4-grams for repetition detection
        ngram_size = 4
        ngrams = [text[i:i + ngram_size] for i in range(len(text) - ngram_size + 1)]

        if not ngrams:
            return 0.0

        unique = len(set(ngrams))
        total = len(ngrams)

        return 1.0 - (unique / total)

    def train_perplexity_model(self, reference_texts: List[str]):
        """Train the perplexity scorer on reference texts.

        Args:
            reference_texts: List of high-quality reference texts.
        """
        self._scorer.train(reference_texts)
        logger.info(f"Perplexity model trained on {len(reference_texts)} texts")

    def get_stats(self) -> Dict:
        """Return filtering statistics."""
        return dict(self._stats)

    def reset(self):
        """Reset filter state (dedup hashes and stats)."""
        self._seen_hashes.clear()
        self._stats = {k: 0 for k in self._stats}
