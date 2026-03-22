#!/usr/bin/env python3
"""
Comprehensive analysis of ALL regex patterns in text_cleaner.py
for potential catastrophic backtracking issues.
"""

import re
import time
import sys
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')

from data_processing.text_cleaner import TextCleaner

def test_pattern(name, pattern, text, flags=0, replacement=None):
    """Test a regex pattern with timeout detection."""
    print(f"\n{name}:")
    print(f"  Pattern: {pattern}")
    print(f"  Input size: {len(text)} bytes")
    
    start = time.time()
    try:
        if replacement:
            result = re.sub(pattern, replacement, text, flags=flags)
        else:
            result = re.split(pattern, text)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.4f}s")
        return elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  Error after {elapsed:.4f}s: {e}")
        return elapsed

def test_punct_patterns():
    """Test punct_patterns from __init__."""
    print("=" * 60)
    print("Testing punct_patterns (defined in __init__)")
    print("=" * 60)
    
    patterns = {
        "period": (r"(?<=[一 - 龥])\.(?=[一 - 龥])", r"。"),
        "comma": (r"(?<=[一 - 龥]),(?=[一 - 龥])", r","),
        "colon": (r"(?<=[一 - 龥]):(?=[一 - 龥])", r":"),
        "semicolon": (r"(?<=[一 - 龥]);(?=[一 - 龥])", r";"),
        "question": (r"(?<=[一 - 龥])\?", r"?"),
        "exclaim": (r"(?<=[一 - 龥])!", r"!"),
    }
    
    # Test with large text
    text = "子曰學而時習之" * 2000  # 28KB
    
    for name, (pattern, repl) in patterns.items():
        test_pattern(f"  {name}", pattern, text, replacement=repl)
    
    # Pathological case: many positions where lookbehind matches but lookahead doesn't
    text2 = "字." * 5000 + "x"  # Lookbehind matches, lookahead fails at end
    for name, (pattern, repl) in patterns.items():
        test_pattern(f"  {name} (pathological)", pattern, text2, replacement=repl)

def test_recover_punctuation():
    """Test _recover_punctuation patterns."""
    print("\n" + "=" * 60)
    print("Testing _recover_punctuation")
    print("=" * 60)
    
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    # Normal case
    text1 = "字\n字" * 5000
    test_pattern("  Main pattern (normal)", pattern, text1, re.MULTILINE, r"\1.\n")
    
    # Pathological: many near-matches
    text2 = "a\n " * 10000 + "b"  # char-newline-space (lookahead fails)
    test_pattern("  Main pattern (near-miss)", pattern, text2, re.MULTILINE, r"\1.\n")
    
    # Large OCR-like output
    text3 = "\n".join([f"第 i 章內容" for i in range(5000)])
    test_pattern("  Main pattern (OCR-like)", pattern, text3, re.MULTILINE, r"\1.\n")

def test_normalize_whitespace():
    """Test _normalize_whitespace patterns."""
    print("\n" + "=" * 60)
    print("Testing _normalize_whitespace")
    print("=" * 60)
    
    patterns = [
        (r"[ \t]+", " "),
        (r"\n\s*\n", "\n"),
        (r" *\n *", "\n"),
    ]
    
    # Test with lots of whitespace
    text1 = " " * 50000
    test_pattern("  Whitespace collapse", patterns[0][0], text1, replacement=patterns[0][1])
    
    text2 = "\n" * 50000
    test_pattern("  Newline collapse", patterns[1][0], text2, replacement=patterns[1][1])
    
    # Mixed whitespace - POTENTIALLY PROBLEMATIC
    # \s* can match varying amounts, creating backtracking
    text3 = (" \n\t\n  \n   \n") * 2000
    test_pattern("  Mixed whitespace", patterns[1][0], text3, replacement=patterns[1][1])
    
    # Alternating spaces and newlines
    text4 = " \n" * 20000
    test_pattern("  Alternating space/newline", patterns[2][0], text4, replacement=patterns[2][1])

def test_split_sentences():
    """Test _split_sentences pattern."""
    print("\n" + "=" * 60)
    print("Testing _split_sentences")
    print("=" * 60)
    
    pattern = r"((?:[。！？；]\s*)+)"
    
    # Normal case
    text1 = "子曰。" * 2000
    test_pattern("  Sentence split (normal)", pattern, text1)
    
    # Pathological: punctuation with varying whitespace
    # The (?:...)+ with \s* inside can cause issues
    text2 = ("。 " * 100 + "!") * 50
    test_pattern("  Sentence split (varying ws)", pattern, text2)
    
    # Many consecutive punctuation marks
    text3 = "。！？；" * 5000
    test_pattern("  Sentence split (consecutive)", pattern, text3)
    
    # Edge case: punctuation at very end with no space
    text4 = "word. " * 5000
    test_pattern("  Sentence split (ASCII punct)", pattern, text4)

def test_strip_annotations():
    """Test _strip_annotations patterns - THESE ARE HIGH RISK."""
    print("\n" + "=" * 60)
    print("Testing _strip_annotations (HIGH RISK)")
    print("=" * 60)
    
    patterns = [
        (r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", ""),
        (r"（按 [：:].*?）", ""),
    ]
    
    # Pattern 1: Non-greedy .*? with lookahead - scans entire text
    print("\n  Pattern 1 analysis:")
    print("    Uses .*? which scans character by character")
    print("    Lookahead (?=[\[【]|$) checked at each position")
    print("    Problem: No closing marker = scans to end of text")
    
    # Test: Opening marker with no closing
    text1 = "[注]" + "x" * 50000
    test_pattern("  No closing marker", patterns[0][0], text1, replacement=patterns[0][1])
    
    # Test: Multiple opening markers (each rescans)
    text2 = "".join(["[注]" + "x" * 500 for _ in range(100)])
    test_pattern("  Multiple openings", patterns[0][0], text2, replacement=patterns[0][1])
    
    # Test: Nested-looking markers
    text3 = "[注] outer [注] inner content"
    test_pattern("  Nested markers", patterns[0][0], text3, replacement=patterns[0][1])
    
    # Pattern 2: Similar issue
    print("\n  Pattern 2 analysis:")
    print("    Same .*? pattern with different delimiters")
    
    text4 = "(按：" + "x" * 50000
    test_pattern("  Pattern 2 no closing", patterns[1][0], text4, replacement=patterns[1][1])

def test_full_pipeline():
    """Test the full cleaning pipeline with large input."""
    print("\n" + "=" * 60)
    print("Testing Full Pipeline")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    # Create realistic large OCR output
    print("\nCreating realistic OCR output (~50KB)...")
    lines = []
    for i in range(2000):
        line = f"第{i}章詩經國風周南關關雎鳩在河之洲窈窕淑女君子好逑"
        if i % 10 == 0:
            line += "   \t  "
        if i % 7 == 0:
            line += "[注]some annotation"
        lines.append(line)
    
    text = "\n".join(lines)
    print(f"Input size: {len(text)} bytes ({len(text)/1024:.1f} KB)")
    
    start = time.time()
    result = cleaner.clean(text)
    elapsed = time.time() - start
    
    print(f"Full pipeline time: {elapsed:.4f}s")
    print(f"Output size: {len(result)} bytes")
    
    # Test with even larger input
    print("\nCreating very large OCR output (~200KB)...")
    lines = []
    for i in range(8000):
        line = f"第{i}章詩經國風周南關關雎鳩在河之洲窈窕淑女君子好逑"
        if i % 100 == 0:
            line += "[注]annotation here"
        lines.append(line)
    
    text = "\n".join(lines)
    print(f"Input size: {len(text)} bytes ({len(text)/1024:.1f} KB)")
    
    start = time.time()
    result = cleaner.clean(text)
    elapsed = time.time() - start
    
    print(f"Full pipeline time: {elapsed:.4f}s")
    print(f"Output size: {len(result)} bytes")

def identify_remaining_issues():
    """Identify any remaining potential issues."""
    print("\n" + "=" * 60)
    print("Remaining Potential Issues")
    print("=" * 60)
    
    print("""
1. _strip_annotations pattern: r"[\\[【](?:注 | 按 | 校勘記 | 案)[】\\]].*?(?=[\\[【]|$)"
   - Uses non-greedy .*? which scans character-by-character
   - On large text without closing markers, scans entire remainder
   - With multiple opening markers, rescans from each one
   - Complexity: O(n*m) where n=text size, m=number of markers
   
2. _split_sentences pattern: r"((?:[。！？；]\\s*)+)"
   - Nested quantifiers: (?:...)+ containing \\s*
   - On certain inputs, could cause backtracking
   - Lower risk because punctuation chars are limited set
   
3. _normalize_whitespace pattern: r"\\n\\s*\\n"
   - \\s* is greedy and can match newlines
   - On inputs like \\n\\n\\n\\n..., creates overlapping matches
   - Python's regex engine handles this reasonably well
   
RECOMMENDATION: The _strip_annotations pattern is the highest risk
for performance issues on large inputs with specific patterns.
""")

if __name__ == "__main__":
    test_punct_patterns()
    test_recover_punctuation()
    test_normalize_whitespace()
    test_split_sentences()
    test_strip_annotations()
    test_full_pipeline()
    identify_remaining_issues()
    
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("""
The _recover_punctuation method itself appears to be FIXED.

The current implementation uses:
  r"([\\u4e00-\\u9fffA-Za-z0-9])\\n(?=[\\u4e00-\\u9fffA-Za-z0-9])"

This is a well-behaved pattern with positive character classes,
not the problematic negated class pattern described in the scenario.

However, OTHER methods have potential issues:
- _strip_annotations: High risk with large texts
- _split_sentences: Medium risk with certain patterns
- _normalize_whitespace: Low risk but worth monitoring

If users report hanging, check if strip_annotations is enabled
and if the input contains many [注] markers without closing.
""")
