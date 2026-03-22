"""Deep analysis of regex patterns for catastrophic backtracking vulnerabilities."""

import re
import time


def test_strip_annotations_pattern():
    """Test the _strip_annotations regex patterns - these use lazy quantifiers."""
    print("=" * 60)
    print("Testing _strip_annotations patterns")
    print("=" * 60)
    
    # Pattern 1: Non-greedy match with lookahead
    pattern1 = r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)"
    
    # Pathological input: very long text without closing marker
    pathological = "[" + "注" + "a" * 50000  # No closing bracket
    
    print(f"\nPattern 1: {pattern1}")
    print(f"Testing with {len(pathological)} chars (no closing bracket)...")
    
    start = time.time()
    result = re.sub(pattern1, "", pathological)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")
    
    # Pattern 2: Another non-greedy pattern
    pattern2 = r"（按 [：:].*?）"
    pathological2 = "（按：" + "a" * 50000  # No closing parenthesis
    
    print(f"\nPattern 2: {pattern2}")
    print(f"Testing with {len(pathological2)} chars (no closing paren)...")
    
    start = time.time()
    result = re.sub(pattern2, "", pathological2)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")


def test_whitespace_pattern():
    """Test _normalize_whitespace patterns."""
    print("\n" + "=" * 60)
    print("Testing _normalize_whitespace patterns")
    print("=" * 60)
    
    # Pattern: \n\s*\n - this can be problematic with mixed whitespace
    pattern = r"\n\s*\n"
    
    # Create pathological input with alternating whitespace
    pathological = "\n" + (" " * 1000 + "\n") * 100
    
    print(f"Testing \\n\\s*\\n with {len(pathological)} chars...")
    start = time.time()
    result = re.sub(pattern, "\n", pathological)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")


def test_split_sentences_pattern():
    """Test _split_sentences regex pattern."""
    print("\n" + "=" * 60)
    print("Testing _split_sentences pattern")
    print("=" * 60)
    
    # Pattern: ((?:[。！？；]\s*)+)
    pattern = r"((?:[。！？；]\s*)+)"
    
    # Pathological: many punctuation marks with whitespace
    pathological = "。 " * 5000 + "text"
    
    print(f"Pattern: {pattern}")
    print(f"Testing with {len(pathological)} chars...")
    
    start = time.time()
    result = re.split(pattern, pathological)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s, got {len(result)} parts")
    
    # Another pathological case: no punctuation, just text
    pathological2 = "子" * 50000
    
    print(f"Testing with {len(pathological2)} chars (no punctuation)...")
    start = time.time()
    result = re.split(pattern, pathological2)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s, got {len(result)} parts")


def test_deduplicate_scenario():
    """Test deduplication with pathological inputs."""
    print("\n" + "=" * 60)
    print("Testing deduplication performance")
    print("=" * 60)
    
    from src.data_processing.text_cleaner import TextCleaner
    
    # Many unique sentences (worst case for set-based dedup)
    unique_sentences = [f"Sentence number {i} for testing purposes" for i in range(10000)]
    text = "".join(unique_sentences)
    
    print(f"Testing with {len(text)} chars ({len(unique_sentences)} unique sentences)...")
    
    cleaner = TextCleaner()
    start = time.time()
    result = cleaner._deduplicate(text)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")


def analyze_recover_punctuation_edge_cases():
    """Analyze edge cases for _recover_punctuation that might cause issues."""
    print("\n" + "=" * 60)
    print("Analyzing _recover_punctuation edge cases")
    print("=" * 60)
    
    from src.data_processing.text_cleaner import TextCleaner
    
    # Edge case 1: Very long single line (no newlines)
    long_line = "子" * 100000
    print(f"\nEdge case 1: Single line with {len(long_line)} chars")
    
    cleaner = TextCleaner()
    start = time.time()
    result = cleaner._recover_punctuation(long_line)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")
    
    # Edge case 2: Alternating char and newline
    alternating = "\n".join(["子"] * 10000)
    print(f"\nEdge case 2: {len(alternating)} chars (10000 single-char lines)")
    
    start = time.time()
    result = cleaner._recover_punctuation(alternating)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")
    
    # Edge case 3: Mixed ASCII and Chinese with newlines
    mixed = "\n".join([f"Line{i}子{i}" for i in range(5000)])
    print(f"\nEdge case 3: {len(mixed)} chars (mixed ASCII/Chinese)")
    
    start = time.time()
    result = cleaner._recover_punctuation(mixed)
    elapsed = time.time() - start
    print(f"Result: {elapsed:.3f}s")


def check_regex_catastrophic_patterns():
    """Check for known catastrophic regex patterns."""
    print("\n" + "=" * 60)
    print("Checking for catastrophic regex patterns")
    print("=" * 60)
    
    patterns_to_check = [
        # Pattern, Description, Risk Level
        (r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])", 
         "recover_punctuation main pattern", "LOW - simple capture + lookahead"),
        (r".*?(?=[\[【]|$)", 
         "strip_annotations greedy with lookahead", "MEDIUM - non-greedy but unbounded"),
        (r".*?", 
         "Non-greedy wildcard", "MEDIUM - depends on context"),
        (r"(?:[。！？；]\s*)+", 
         "Sentence splitter with nested quantifier", "LOW - possessive would help"),
    ]
    
    for pattern, desc, risk in patterns_to_check:
        print(f"\n{desc}:")
        print(f"  Pattern: {pattern[:60]}{'...' if len(pattern) > 60 else ''}")
        print(f"  Risk: {risk}")


if __name__ == "__main__":
    check_regex_catastrophic_patterns()
    test_strip_annotations_pattern()
    test_whitespace_pattern()
    test_split_sentences_pattern()
    test_deduplicate_scenario()
    analyze_recover_punctuation_edge_cases()
