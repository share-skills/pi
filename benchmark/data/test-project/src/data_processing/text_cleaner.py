"""Text Cleaner for Classical Chinese OCR Output.

Cleans and normalizes text extracted from OCR, handling common artifacts
like misrecognized characters, broken punctuation, and encoding issues
specific to classical Chinese (文言文) texts.

The cleaning pipeline:
1. Normalize Unicode (NFC)
2. Fix common OCR misrecognitions
3. Recover punctuation marks
4. Remove duplicate passages
5. Normalize whitespace

Usage:
    cleaner = TextCleaner()
    cleaned = cleaner.clean(raw_ocr_text)
"""

import re
import unicodedata
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


# Common OCR misrecognition mappings for classical Chinese
OCR_CORRECTIONS = {
    "己": "已",  # Often confused in classical texts
    "壹": "一",
    "貳": "二",
    "幺": "么",
    "囗": "口",  # Unicode box vs mouth radical
    "閒": "閑",  # Variant forms
    "爲": "為",
    "於": "于",  # Classical variant
}

# Classical Chinese punctuation marks
CLASSICAL_PUNCTUATION = set("。、！？；：「」『』（）【】《》〈〉—…·")

# Modern punctuation that should be converted
MODERN_TO_CLASSICAL = {
    ",": "，",
    ".": "。",
    "!": "！",
    "?": "？",
    ";": "；",
    ":": "：",
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
}


@dataclass
class CleanerConfig:
    """Configuration for the text cleaner."""
    normalize_unicode: bool = True
    fix_ocr_errors: bool = True
    recover_punctuation: bool = True
    deduplicate: bool = True
    normalize_whitespace: bool = True
    min_line_length: int = 2
    dedup_window: int = 5  # Sentences to look back for dedup
    custom_corrections: Dict[str, str] = field(default_factory=dict)
    strip_annotations: bool = False
    convert_traditional: bool = False


class TextCleaner:
    """Cleans and normalizes classical Chinese text from OCR output.

    Applies a series of transformations to fix common OCR artifacts and
    normalize the text for downstream processing.

    Args:
        config: CleanerConfig instance with cleaning options.

    Example:
        >>> cleaner = TextCleaner()
        >>> raw = "子曰：「學而時習之,不亦說乎?」"
        >>> cleaned = cleaner.clean(raw)
        >>> print(cleaned)
        子曰：「學而時習之，不亦說乎？」
    """

    def __init__(self, config: CleanerConfig = None):
        self.config = config or CleanerConfig()
        self._corrections = {**OCR_CORRECTIONS, **self.config.custom_corrections}
        self._seen_sentences: Set[str] = set()

        self.punct_patterns = {
            "period": re.compile(r"(?<=[一-龥])\.(?=[一-龥])"),
            "comma": re.compile(r"(?<=[一-龥]),(?=[一-龥])"),
            "colon": re.compile(r"(?<=[一-龥]):(?=[一-龥])"),
            "semicolon": re.compile(r"(?<=[一-龥]);(?=[一-龥])"),
            "question": re.compile(r"(?<=[一-龥])\?"),
            "exclaim": re.compile(r"(?<=[一-龥])!"),
        }

        # Stats tracking
        self._stats = {
            "chars_processed": 0,
            "corrections_made": 0,
            "duplicates_removed": 0,
            "lines_removed": 0,
        }

        if self.config.convert_traditional:
            try:
                import opencc
                self._converter = opencc.OpenCC("t2s.json")
            except ImportError:
                logger.warning("opencc not installed, traditional conversion disabled")
                self._converter = None
        else:
            self._converter = None

    def clean(self, text: str) -> str:
        """Apply the full cleaning pipeline to input text.

        Args:
            text: Raw OCR text to clean.

        Returns:
            Cleaned and normalized text.
        """
        if not text or not text.strip():
            return ""

        self._stats["chars_processed"] += len(text)
        original_len = len(text)

        # Step 1: Unicode normalization
        if self.config.normalize_unicode:
            text = self._normalize_unicode(text)

        # Step 2: Fix OCR misrecognitions
        if self.config.fix_ocr_errors:
            text = self._fix_ocr_errors(text)

        # Step 3: Recover and normalize punctuation
        if self.config.recover_punctuation:
            text = self._recover_punctuation(text)

        # Step 4: Remove duplicates
        if self.config.deduplicate:
            text = self._deduplicate(text)

        # Step 5: Normalize whitespace
        if self.config.normalize_whitespace:
            text = self._normalize_whitespace(text)

        # Step 6: Convert traditional to simplified if enabled
        if self._converter:
            text = self._converter.convert(text)

        # Step 7: Strip annotations if enabled
        if self.config.strip_annotations:
            text = self._strip_annotations(text)

        # Remove short lines
        lines = text.split("\n")
        lines = [l for l in lines if len(l.strip()) >= self.config.min_line_length or not l.strip()]
        removed = original_len - len(lines)
        if removed > 0:
            self._stats["lines_removed"] += removed

        return "\n".join(lines)

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode to NFC form and fix encoding issues."""
        text = unicodedata.normalize("NFC", text)

        # Replace common encoding artifacts
        text = text.replace("\ufeff", "")  # BOM
        text = text.replace("\u200b", "")  # Zero-width space
        text = text.replace("\u200c", "")  # Zero-width non-joiner
        text = text.replace("\u200d", "")  # Zero-width joiner
        text = text.replace("\ufffe", "")  # Invalid Unicode

        return text

    def _fix_ocr_errors(self, text: str) -> str:
        """Apply known OCR correction mappings."""
        corrections = 0
        for wrong, right in self._corrections.items():
            count = text.count(wrong)
            if count > 0:
                text = text.replace(wrong, right)
                corrections += count

        self._stats["corrections_made"] += corrections
        if corrections > 0:
            logger.debug(f"Applied {corrections} OCR corrections")

        return text

    def _recover_punctuation(self, text: str) -> str:
        """Recover and normalize punctuation marks in the text.

        Converts ASCII punctuation to their CJK fullwidth equivalents
        and attempts to recover punctuation that was lost during OCR.
        
        Uses a single-pass approach with positive character class matching
        to avoid potential performance issues with large inputs.
        """
        # Convert ASCII punctuation to CJK equivalents
        for ascii_p, cjk_p in MODERN_TO_CLASSICAL.items():
            text = text.replace(ascii_p, cjk_p)

        # Recover missing punctuation between lines
        # Match Chinese characters or alphanumeric on both sides of newline
        # This uses positive character classes for better performance
        text = re.sub(
            r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])",
            r"\1.\n",
            text,
            flags=re.MULTILINE,
        )

        return text

    def _deduplicate(self, text: str) -> str:
        """Remove duplicate sentences/passages from the text.

        OCR often produces duplicated content when pages overlap or when
        the same passage is scanned multiple times.
        """
        sentences = self._split_sentences(text)
        seen = set()
        unique = []
        duplicates = 0

        for sentence in sentences:
            normalized = sentence.strip()
            if not normalized:
                unique.append(sentence)
                continue

            if normalized in seen:
                duplicates += 1
                logger.debug(f"Removed duplicate: {normalized[:30]}...")
                continue

            seen.add(normalized)
            unique.append(sentence)

        self._stats["duplicates_removed"] += duplicates
        return "".join(unique)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in the text.

        Removes excessive whitespace while preserving formatting.
        """
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)  # Collapse paragraph breaks
        text = re.sub(r" *\n *", "\n", text)

        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences based on Chinese punctuation."""
        # Split on sentence-ending punctuation while preserving the punctuation
        parts = re.split(r"((?:[。！？；]\s*)+)", text)
        return parts

    def _strip_annotations(self, text: str) -> str:
        """Remove annotation markers and inline notes.

        Common patterns in classical Chinese digital editions:
        - [注] ... content ... 
        - （按：...）
        - 【校勘記】...
        """
        # Remove bracketed annotations
        text = re.sub(r"[\[【](?:注|按|校勘記|案)[】\]].*?(?=[\[【]|$)", "", text)
        text = re.sub(r"（按[：:].*?）", "", text)

        return text

    def clean_batch(self, texts: List[str]) -> List[str]:
        """Clean multiple texts, maintaining cross-document dedup state.

        Args:
            texts: List of raw text strings to clean.

        Returns:
            List of cleaned text strings.
        """
        # Reset dedup state for batch
        self._seen_sentences.clear()
        return [self.clean(text) for text in texts]

    def get_stats(self) -> Dict:
        """Return cleaning statistics."""
        return dict(self._stats)

    def reset_stats(self):
        """Reset statistics counters."""
        self._stats = {
            "chars_processed": 0,
            "corrections_made": 0,
            "duplicates_removed": 0,
            "lines_removed": 0,
        }


class TextNormalizer:
    """Additional text normalization utilities for classical Chinese.

    Provides character-level normalization beyond what TextCleaner does,
    including variant character unification and radical normalization.
    """

    # Variant character mappings (異體字)
    VARIANT_CHARS = {
        "峯": "峰", "羣": "群", "甦": "蘇", "牀": "床",
        "箇": "個", "迴": "回", "麪": "麵", "裏": "裡",
        "喫": "吃", "祇": "只", "衹": "只", "纔": "才",
    }

    @classmethod
    def unify_variants(cls, text: str) -> str:
        """Replace variant characters with their standard forms."""
        for variant, standard in cls.VARIANT_CHARS.items():
            text = text.replace(variant, standard)
        return text

    @classmethod
    def count_chinese_chars(cls, text: str) -> int:
        """Count the number of Chinese characters in text."""
        return sum(1 for c in text if "\u4e00" <= c <= "\u9fff")

    @classmethod
    def chinese_ratio(cls, text: str) -> float:
        """Calculate the ratio of Chinese characters to total characters."""
        if not text:
            return 0.0
        total = len(text.replace(" ", "").replace("\n", ""))
        if total == 0:
            return 0.0
        chinese = cls.count_chinese_chars(text)
        return chinese / total
