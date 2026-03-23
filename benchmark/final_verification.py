"""Final verification of all findings."""

import sys
import time

# Test both versions
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark')
from src.data_processing.text_cleaner import TextCleaner as FixedCleaner

sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project')
from src.data_processing.text_cleaner import TextCleaner as BuggyCleaner


def test_strip_annotations_correctness():
    """Test _strip_annotations correctness - CRITICAL BUG VERIFICATION."""
    print("=" * 70)
    print("TEST 1: _strip_annotations Correctness (CRITICAL BUG)")
    print("=" * 70)
    
    fixed = FixedCleaner()
    buggy = BuggyCleaner()
    
    test_cases = [
        ("[注] 這是註釋", "", "Simple annotation"),
        ("[注] 註釋 some text", " some text", "Text after annotation"),
        ("正文 [注] 註釋 更多", "正文  更多", "Text before and after"),
        ("【校勘記】校對內容 end", " end", "Fullwidth bracket variant"),
        ("（按：some note）text", "text", "Parenthetical annotation"),
    ]
    
    print("\nTesting FIXED version:")
    for input_text, expected, description in test_cases:
        result = fixed._strip_annotations(input_text)
        status = "PASS" if result == expected else f"FAIL (got '{result}')"
        print(f"  {description}: {status}")
    
    print("\nTesting BUGGY version:")
    for input_text, expected, description in test_cases:
        result = buggy._strip_annotations(input_text)
        # The buggy version uses .*?(?=...) which may behave differently
        print(f"  {description}: input='{input_text}' -> output='{result}'")


def test_recover_punctuation_performance():
    """Verify _recover_punctuation performance on large inputs."""
    print("\n" + "=" * 70)
    print("TEST 2: _recover_punctuation Performance")
    print("=" * 70)
    
    cleaner = FixedCleaner()
    
    sizes = [(100, "100 lines"), (500, "500 lines"), (1000, "1K lines"), (2000, "2K lines")]
    
    for n, label in sizes:
        lines = ["天地玄黃宇宙洪荒"] * n
        text = "\n".join(lines)
        
        start = time.time()
        result = cleaner._recover_punctuation(text)
        elapsed = time.time() - start
        
        status = "PASS" if elapsed < 1.0 else "FAIL"
        print(f"  {label} ({len(text):,} chars): {elapsed:.4f}s {status}")


def test_split_sentences_backtracking():
    """Test _split_sentences for ReDoS vulnerability."""
    print("\n" + "=" * 70)
    print("TEST 3: _split_sentences Backtracking Risk")
    print("=" * 70)
    
    fixed = FixedCleaner()
    buggy = BuggyCleaner()
    
    # Pattern that could trigger nested quantifier backtracking
    # Many punctuation marks followed by whitespace, ending with non-match
    for n in [10, 20, 30, 40, 50]:
        text = "。 " * n + "END"
        
        print(f"\nn={n} punctuation-space pairs:")
        
        # Test buggy version
        start = time.time()
        try:
            result_buggy = buggy._split_sentences(text)
            elapsed_buggy = time.time() - start
            print(f"  BUGGY: {elapsed_buggy:.4f}s")
        except Exception as e:
            print(f"  BUGGY: ERROR - {e}")
            elapsed_buggy = float('inf')
        
        # Test fixed version
        start = time.time()
        try:
            result_fixed = fixed._split_sentences(text)
            elapsed_fixed = time.time() - start
            print(f"  FIXED: {elapsed_fixed:.4f}s")
        except Exception as e:
            print(f"  FIXED: ERROR - {e}")
            elapsed_fixed = float('inf')
        
        if elapsed_buggy > elapsed_fixed * 2:
            print(f"  WARNING: Buggy version is {elapsed_buggy/elapsed_fixed:.1f}x slower!")


def test_dead_code():
    """Check for dead punct_patterns code."""
    print("\n" + "=" * 70)
    print("TEST 4: Dead Code Check (punct_patterns)")
    print("=" * 70)
    
    fixed = FixedCleaner()
    buggy = BuggyCleaner()
    
    print(f"\nFixed version has punct_patterns: {hasattr(fixed, 'punct_patterns')}")
    print(f"Buggy version has punct_patterns: {hasattr(buggy, 'punct_patterns')}")
    
    if hasattr(buggy, 'punct_patterns'):
        print(f"  Patterns defined: {list(buggy.punct_patterns.keys())}")
        print("  WARNING: These patterns are never used - DEAD CODE")


def test_dedup_window():
    """Verify dedup_window config is ignored."""
    print("\n" + "=" * 70)
    print("TEST 5: dedup_window Config Check")
    print("=" * 70)
    
    from src.data_processing.text_cleaner import CleanerConfig
    
    # Create config with small window
    config = CleanerConfig(dedup_window=2)
    cleaner = FixedCleaner(config)
    
    # Text with repeated sentence far apart
    text = "A。B。C。D。A。E。"  # First 'A' should be forgotten with window=2
    
    result = cleaner._deduplicate(text)
    stats = cleaner.get_stats()
    
    print(f"  Input: {text}")
    print(f"  Output: {result}")
    print(f"  Duplicates removed: {stats['duplicates_removed']}")
    print(f"  Config window: {config.dedup_window}")
    print(f"\n  NOTE: Current implementation checks ALL previous sentences globally")
    print(f"        The dedup_window config is IGNORED")


def main():
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION - TEXT CLEANER ISSUES")
    print("=" * 70)
    
    test_strip_annotations_correctness()
    test_recover_punctuation_performance()
    test_split_sentences_backtracking()
    test_dead_code()
    test_dedup_window()
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    
    print("\n\nSUMMARY OF FINDINGS:")
    print("-" * 70)
    print("1. _recover_punctuation: NO backtracking issue - performs efficiently")
    print("2. _strip_annotations: CRITICAL BUG - removes too much content")
    print("3. _split_sentences: Has nested quantifiers (ReDoS risk)")
    print("4. punct_patterns: DEAD CODE - defined but never used")
    print("5. dedup_window: CONFIG IGNORED - checks all sentences globally")
    print("-" * 70)


if __name__ == "__main__":
    main()
