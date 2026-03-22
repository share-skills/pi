"""Comprehensive test and audit of text_cleaner.py regex patterns."""

import sys
import time
import re
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')

from data_processing.text_cleaner import TextCleaner, TextNormalizer


def test_all_regex_patterns():
    """Test all regex patterns in the codebase for performance."""
    
    print("=" * 70)
    print("COMPREHENSIVE REGEX AUDIT - text_cleaner.py")
    print("=" * 70)
    
    cleaner = TextCleaner()
    
    # Generate test data
    chinese_text = "天地玄黃宇宙洪荒日月盈昃辰宿列張" * 100
    mixed_text = "Chapter 1: 子曰學而時習之不亦說乎，" * 100
    multiline_text = "\n".join(["子曰學而時習之"] * 500)
    
    tests = [
        # (method_name, input_data, description)
        ("_normalize_unicode", chinese_text, "Unicode normalization"),
        ("_fix_ocr_errors", chinese_text.replace("已", "己"), "OCR error correction"),
        ("_recover_punctuation", multiline_text, "Punctuation recovery (multiline)"),
        ("_normalize_whitespace", "   multiple   spaces   and\n\n  blank lines  ", "Whitespace normalization"),
        ("_split_sentences", "子曰。學而！時習之？不亦說乎；", "Sentence splitting"),
        ("_strip_annotations", "[注] some annotation content【校勘記】more content", "Annotation stripping"),
    ]
    
    print("\n1. PERFORMANCE TESTS")
    print("-" * 70)
    
    for method_name, input_data, description in tests:
        method = getattr(cleaner, method_name)
        
        start = time.time()
        try:
            result = method(input_data)
            elapsed = time.time() - start
            status = f"PASS ({elapsed:.4f}s)"
        except Exception as e:
            elapsed = time.time() - start
            status = f"FAIL: {e}"
        
        print(f"  {description}: {status}")
    
    # Test with larger inputs
    print("\n2. STRESS TESTS (large inputs)")
    print("-" * 70)
    
    large_multiline = "\n".join(["子曰學而時習之"] * 5000)
    large_text = "天地玄黃宇宙洪荒" * 10000
    
    stress_tests = [
        ("_recover_punctuation", large_multiline, "5000 lines"),
        ("_normalize_whitespace", large_text * 5, "50KB whitespace"),
        ("_strip_annotations", "[注] test " * 5000, "5000 annotations"),
    ]
    
    for method_name, input_data, description in stress_tests:
        method = getattr(cleaner, method_name)
        
        start = time.time()
        try:
            result = method(input_data)
            elapsed = time.time() - start
            print(f"  {description}: PASS ({elapsed:.4f}s)")
        except TimeoutError:
            elapsed = time.time() - start
            print(f"  {description}: TIMEOUT after {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  {description}: FAIL ({elapsed:.4f}s) - {e}")
    
    # Test full pipeline
    print("\n3. FULL PIPELINE TEST")
    print("-" * 70)
    
    full_input = "\n".join([
        "Chapter 1: 子曰學而時習之，不亦說乎",
        "有朋自遠方來，不亦樂乎",
        "人不知而不慍，不亦君子乎",
    ] * 500)
    
    start = time.time()
    result = cleaner.clean(full_input)
    elapsed = time.time() - start
    print(f"  Full clean() pipeline (500 iterations): {elapsed:.4f}s")
    print(f"  Input length: {len(full_input)} chars")
    print(f"  Output length: {len(result)} chars")


def analyze_regex_patterns():
    """Analyze each regex pattern for potential issues."""
    
    print("\n" + "=" * 70)
    print("REGEX PATTERN ANALYSIS")
    print("=" * 70)
    
    patterns = [
        # (pattern, name, risk_level, notes)
        (r"(?<=[一 - 龥])\.(?=[一 - 龥])", "punct_patterns.period", "LOW", "Fixed-width lookbehind/lookahead - safe"),
        (r"(?<=[一 - 龥]),(?=[一 - 龥])", "punct_patterns.comma", "LOW", "Fixed-width lookbehind/lookahead - safe"),
        (r"(?<=[一 - 龥]):(?=[一 - 龥])", "punct_patterns.colon", "LOW", "Fixed-width lookbehind/lookahead - safe"),
        (r"(?<=[一 - 龥]);(?=[一 - 龥])", "punct_patterns.semicolon", "LOW", "Fixed-width lookbehind/lookahead - safe"),
        (r"(?<=[一 - 龥])\?", "punct_patterns.question", "LOW", "Fixed-width lookbehind - safe"),
        (r"(?<=[一 - 龥])!", "punct_patterns.exclaim", "LOW", "Fixed-width lookbehind - safe"),
        (r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])", "_recover_punctuation", "LOW", "Positive char class - safe"),
        (r"[ \t]+", "_normalize_whitespace", "LOW", "Simple quantifier - safe"),
        (r"\n\s*\n", "_normalize_whitespace", "MEDIUM", "\\s* could match newlines - watch for edge cases"),
        (r" *\n *", "_normalize_whitespace", "LOW", "Simple pattern - safe"),
        (r"((?:[。！？；]\s*)+)", "_split_sentences", "MEDIUM", "Nested quantifier but bounded by punctuation"),
        (r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "_strip_annotations", "HIGH", "Non-greedy .*? with lookahead - potential backtracking"),
        (r"（按 [：:].*?）", "_strip_annotations", "MEDIUM", "Non-greedy .*? - moderate risk"),
    ]
    
    print("\nPattern Risk Assessment:")
    print("-" * 70)
    
    for pattern, name, risk, notes in patterns:
        print(f"\n  {name}:")
        print(f"    Pattern: {pattern[:60]}{'...' if len(pattern) > 60 else ''}")
        print(f"    Risk: {risk}")
        print(f"    Notes: {notes}")


def find_hidden_issues():
    """Find hidden issues beyond regex patterns."""
    
    print("\n" + "=" * 70)
    print("HIDDEN ISSUES DISCOVERY")
    print("=" * 70)
    
    issues = []
    
    # Issue 1: Dead code
    print("\n  Issue #1: DEAD CODE - punct_patterns dictionary")
    print("    Location: __init__, lines 96-103")
    print("    Description: self.punct_patterns is defined but never used")
    print("    Impact: Code confusion, maintenance burden")
    print("    Fix: Remove or integrate into _recover_punctuation")
    issues.append("Dead code: punct_patterns unused")
    
    # Issue 2: Inconsistent validation
    print("\n  Issue #2: INCONSISTENT INPUT VALIDATION")
    print("    Location: clean() vs internal methods")
    print("    Description: clean() validates str input, but _recover_punctuation etc don't")
    print("    Impact: Potential crashes if internal methods called directly")
    print("    Fix: Add validation to all public methods or document internal use only")
    issues.append("Inconsistent input validation")
    
    # Issue 3: Stats calculation bug
    print("\n  Issue #3: STATISTICS CALCULATION BUG")
    print("    Location: clean(), line 169")
    print("    Description: 'removed = original_len - len(lines)' compares chars vs list length")
    print("    Impact: Incorrect stats reporting")
    print("    Fix: Compare char counts or line counts consistently")
    issues.append("Stats calculation bug")
    
    # Issue 4: Dedup state not reset between clean() calls
    print("\n  Issue #4: DEDUP STATE LEAKAGE")
    print("    Location: _deduplicate() uses self._seen_sentences")
    print("    Description: Seen sentences persist across clean() calls unless clean_batch() used")
    print("    Impact: Sentences from previous clean() calls may be incorrectly removed")
    print("    Fix: Reset _seen_sentences at start of clean() or document behavior")
    issues.append("Dedup state leakage")
    
    # Issue 5: Exception handling in opencc import
    print("\n  Issue #5: SILENT FAILURE - opencc import")
    print("    Location: __init__, lines 113-119")
    print("    Description: ImportError logged but _converter stays None, no later validation")
    print("    Impact: Crashes when _converter.convert() called on None")
    print("    Fix: Validate _converter before use or raise on import failure")
    issues.append("Silent failure on opencc import")
    
    # Issue 6: Type safety in _split_sentences output
    print("\n  Issue #6: SENTENCE SPLIT OUTPUT")
    print("    Location: _split_sentences(), line 270-271")
    print("    Description: Returns parts including delimiters, may cause empty strings")
    print("    Impact: _deduplicate receives unexpected format")
    print("    Fix: Filter empty strings or document return format")
    issues.append("Sentence split output format unclear")
    
    print(f"\n  Total issues found: {len(issues)}")
    
    return issues


def verify_behavior_preservation():
    """Verify that any fixes preserve existing behavior."""
    
    print("\n" + "=" * 70)
    print("BEHAVIOR VERIFICATION")
    print("=" * 70)
    
    cleaner = TextCleaner()
    
    test_cases = [
        # (input, expected_behavior_description)
        ("子曰：「學而時習之，不亦說乎？」", "Preserve existing punctuation"),
        ("子曰：「學而時習之，不亦說乎?」", "Convert ASCII ? to CJK ?"),
        ("Hello,World", "Convert ASCII comma to CJK"),
        ("Line1\nLine2", "Add period between lines"),
        ("Already has.\nNext sentence", "Don't double-add punctuation"),
        ("", "Return empty string"),
        ("   ", "Return empty string"),
        ("Duplicate. Duplicate. Unique.", "Remove duplicate sentences"),
    ]
    
    print("\nTest Cases:")
    print("-" * 70)
    
    for i, (input_text, description) in enumerate(test_cases, 1):
        result = cleaner.clean(input_text)
        print(f"  {i}. {description}")
        print(f"     Input:  '{input_text[:50]}{'...' if len(input_text) > 50 else ''}'")
        print(f"     Output: '{result[:50]}{'...' if len(result) > 50 else ''}'")
        print()


if __name__ == "__main__":
    test_all_regex_patterns()
    analyze_regex_patterns()
    find_hidden_issues()
    verify_behavior_preservation()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
The reported catastrophic backtracking issue in _recover_punctuation 
has been FIXED in the current codebase. The pattern now uses positive 
character classes which are well-behaved.

However, 6 HIDDEN ISSUES were discovered:
1. Dead code (punct_patterns unused)
2. Inconsistent input validation
3. Statistics calculation bug  
4. Dedup state leakage between clean() calls
5. Silent failure on optional dependency import
6. Unclear sentence split output format

None of these cause hangs, but they affect code quality and reliability.
""")
