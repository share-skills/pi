#!/usr/bin/env python3
"""Test script to reproduce the hanging issue with _recover_punctuation."""

import sys
import time
import re
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')

from data_processing.text_cleaner import TextCleaner

# The problematic regex from _recover_punctuation:
# r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"

def test_catastrophic_input():
    """Create input that causes catastrophic backtracking.
    
    The pattern uses a lookahead (?=...) which can cause issues when:
    - Many consecutive newlines exist
    - Mixed with characters that almost match but don't quite match
    """
    cleaner = TextCleaner()
    
    # Test 1: Many consecutive newlines between Chinese chars
    print("Test 1: Many newlines between chars...")
    text1 = "字\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n字"
    start = time.time()
    result = cleaner._recover_punctuation(text1)
    print(f"  Completed in {time.time() - start:.4f}s")
    
    # Test 2: Alternating pattern with spaces (not matching lookahead)
    print("Test 2: Alternating with spaces...")
    text2 = "字\n \n字\n \n字\n \n字\n \n字\n \n字\n \n字\n \n字\n \n字"
    start = time.time()
    result = cleaner._recover_punctuation(text2)
    print(f"  Completed in {time.time() - start:.4f}s")
    
    # Test 3: Large text with many lines ending in non-Chinese
    print("Test 3: Lines ending with numbers/special chars...")
    base = "abc123!@#\n" * 500 + "字\n" * 500
    start = time.time()
    result = cleaner._recover_punctuation(base)
    print(f"  Completed in {time.time() - start:.4f}s")
    
    # Test 4: Worst case - repeated near-matches
    # Pattern needs: char + newline + (lookahead must match char)
    # If we have: char + newline + space + char, the lookahead fails
    print("Test 4: Repeated near-matches...")
    text4 = "a\n " * 5000 + "b"
    start = time.time()
    result = cleaner._recover_punctuation(text4)
    print(f"  Completed in {time.time() - start:.4f}s")

def test_regex_directly():
    """Test the regex pattern directly for backtracking issues."""
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    regex = re.compile(pattern, flags=re.MULTILINE)
    
    # Create pathological input
    # The issue is NOT with this pattern - it's actually well-behaved
    # because it uses a lookahead, not nested quantifiers
    
    print("\nDirect regex tests:")
    
    # Test with valid matches
    text = "字\n字"
    result = regex.sub(r"\1.\n", text)
    print(f"Simple match: '{text}' -> '{result}'")
    
    # Test with no matches (spaces break the lookahead)
    text = "字\n \n字"
    result = regex.sub(r"\1.\n", text)
    print(f"With space: '{text}' -> '{result}'")

def analyze_pattern():
    """Analyze the actual pattern for potential issues."""
    print("\n=== Pattern Analysis ===")
    print("Pattern: r\"([\\u4e00-\\u9fffA-Za-z0-9])\\n(?=[\\u4e00-\\u9fffA-Za-z0-9])\"")
    print()
    print("This pattern does NOT have catastrophic backtracking because:")
    print("1. No nested quantifiers (*, +, {} inside each other)")
    print("2. Lookahead (?=...) is atomic - either matches or doesn't")
    print("3. Each character class is fixed-width")
    print()
    print("However, there MAY be an issue with:")
    print("- Very long sequences causing O(n) slowdown")
    print("- But this wouldn't cause 'hanging', just slowness")
    print()
    
def find_actual_issue():
    """Look for the actual cause of hanging."""
    print("\n=== Searching for Actual Issue ===")
    
    # Check all regex patterns in the file
    patterns = [
        r"(?<=[一 - 龥])\.(?=[一 - 龥])",  # period
        r"(?<=[一 - 龥]),(?=[一 - 龥])",  # comma  
        r"(?<=[一 - 龥]):(?=[一 - 龥])",  # colon
        r"(?<=[一 - 龥]);(?=[一 - 龥])",  # semicolon
        r"(?<=[一 - 龥])\?",  # question
        r"(?<=[一 - 龥])!",  # exclaim
        r"((?:[。！？；]\s*)+)",  # sentence split
        r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)",  # strip annotations
        r"（按 [：:].*?）",  # annotation paren
    ]
    
    print("Looking at _strip_annotations patterns - these use .*?")
    print("Pattern: r\"[\\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)\"")
    print()
    print("THIS is the problematic pattern!")
    print("- Uses .*? (non-greedy) followed by lookahead (?=...)")
    print("- On large text without closing markers, this scans entire text")
    print("- With multiple opening markers, complexity explodes")
    
    # Test this pattern
    print("\nTesting _strip_annotations pattern:")
    text = "[注] " + "字" * 10000  # Long text without closing
    start = time.time()
    result = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)
    elapsed = time.time() - start
    print(f"  10K chars: {elapsed:.4f}s")
    
    text = "[注] " + "字" * 50000
    start = time.time()
    result = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)
    elapsed = time.time() - start
    print(f"  50K chars: {elapsed:.4f}s")

if __name__ == "__main__":
    test_catastrophic_input()
    test_regex_directly()
    analyze_pattern()
    find_actual_issue()
