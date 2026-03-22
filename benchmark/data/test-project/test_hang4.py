#!/usr/bin/env python3
"""
Reproduce the exact hang scenario described in the issue.

The issue states: "_recover_punctuation method never returns for texts >10KB"

Let me try various pathological inputs that could cause catastrophic backtracking.
"""

import sys
import time
import re
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')

from data_processing.text_cleaner import TextCleaner

def test_specific_ocr_pattern():
    """Test with specific OCR output patterns."""
    print("=== Testing specific OCR patterns ===")
    
    cleaner = TextCleaner()
    
    # Pattern 1: OCR output with broken lines (character by character)
    # This creates: char\nchar\nchar\n... 
    # The regex needs to check each \n with lookahead
    print("\n1. Character-by-character OCR output:")
    text = "\n".join("學而時習之不亦說乎有朋自遠方來不亦樂乎")
    text = (text + "\n") * 500  # Repeat to get >10KB
    print(f"   Size: {len(text)} bytes")
    start = time.time()
    result = cleaner._recover_punctuation(text)
    print(f"   Time: {time.time() - start:.4f}s")
    
    # Pattern 2: Mixed ASCII and Chinese with newlines
    print("\n2. Mixed ASCII/Chinese with newlines:")
    lines = []
    for i in range(2000):
        lines.append(f"Line{i}:中文測試abc123")
    text = "\n".join(lines)
    print(f"   Size: {len(text)} bytes")
    start = time.time()
    result = cleaner._recover_punctuation(text)
    print(f"   Time: {time.time() - start:.4f}s")
    
    # Pattern 3: Lines ending with punctuation that should NOT match
    print("\n3. Lines ending with punctuation:")
    lines = []
    for i in range(3000):
        lines.append(f"第{i}章。")
    text = "\n".join(lines)
    print(f"   Size: {len(text)} bytes")
    start = time.time()
    result = cleaner._recover_punctuation(text)
    print(f"   Time: {time.time() - start:.4f}s")

def test_regex_with_timeout(pattern, text, replacement, flags=0, timeout=5):
    """Test regex with timeout to detect hanging."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Regex timed out after {timeout}s")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        start = time.time()
        result = re.sub(pattern, replacement, text, flags=flags)
        signal.alarm(0)  # Cancel alarm
        return time.time() - start, result
    except TimeoutError as e:
        signal.alarm(0)
        raise e
    finally:
        signal.signal(signal.SIGALRM, old_handler)

def test_pathological_cases():
    """Test truly pathological cases that might hang."""
    print("\n=== Testing Pathological Cases ===")
    
    # The pattern from _recover_punctuation:
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    # Case 1: Very long line followed by many short lines
    # This tests if there's any buffering/processing issue
    print("\n1. One huge line + many small lines:")
    text = "x" * 50000 + "\n" + "\n".join(["y"] * 1000)
    print(f"   Size: {len(text)} bytes")
    try:
        elapsed, _ = test_regex_with_timeout(pattern, text, r"\1.\n", re.MULTILINE, timeout=5)
        print(f"   Time: {elapsed:.4f}s")
    except TimeoutError as e:
        print(f"   HUNG: {e}")
    
    # Case 2: Alternating matching/non-matching contexts
    # a\nb matches, a\n b doesn't (space breaks lookahead)
    print("\n2. Alternating match/no-match:")
    text = ""
    for i in range(10000):
        if i % 2 == 0:
            text += "a\nb\n"  # Should match
        else:
            text += "a\n b\n"  # Should NOT match (space)
    print(f"   Size: {len(text)} bytes")
    try:
        elapsed, _ = test_regex_with_timeout(pattern, text, r"\1.\n", re.MULTILINE, timeout=5)
        print(f"   Time: {elapsed:.4f}s")
    except TimeoutError as e:
        print(f"   HUNG: {e}")
    
    # Case 3: Unicode edge cases
    # Characters at boundaries of the unicode ranges
    print("\n3. Unicode boundary characters:")
    text = ""
    for i in range(5000):
        # \u4e00 is first CJK char, \u9fff is last
        text += "\u4e00\n\u9fff\n"
    print(f"   Size: {len(text)} bytes")
    try:
        elapsed, _ = test_regex_with_timeout(pattern, text, r"\1.\n", re.MULTILINE, timeout=5)
        print(f"   Time: {elapsed:.4f}s")
    except TimeoutError as e:
        print(f"   HUNG: {e}")
    
    # Case 4: Many consecutive newlines (empty lines)
    print("\n4. Many consecutive newlines:")
    text = "字" + "\n\n\n\n\n" * 5000 + "字"
    print(f"   Size: {len(text)} bytes")
    try:
        elapsed, _ = test_regex_with_timeout(pattern, text, r"\1.\n", re.MULTILINE, timeout=5)
        print(f"   Time: {elapsed:.4f}s")
    except TimeoutError as e:
        print(f"   HUNG: {e}")

def analyze_actual_regex_behavior():
    """Analyze exactly what the regex does step by step."""
    print("\n=== Regex Behavior Analysis ===")
    
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    test_cases = [
        "字\n字",       # Simple match
        "字\n \n字",    # Space breaks it
        "字\n",         # No char after newline
        "\n字",         # No char before newline
        "字\n字\n字",   # Multiple matches
        "a\nb",         # ASCII match
        "1\n2",         # Numeric match
    ]
    
    for test in test_cases:
        result = re.sub(pattern, r"\1.\n", test, flags=re.MULTILINE)
        print(f"   '{test}' -> '{result}'")

def create_worst_case_input():
    """Create the worst possible input for this regex."""
    print("\n=== Worst Case Input Test ===")
    
    cleaner = TextCleaner()
    
    # The regex engine processes left-to-right
    # At each position, it tries to match:
    # 1. A character in the class
    # 2. Followed by newline
    # 3. With lookahead for another character
    #
    # Worst case would be:
    # - Many positions where (1) and (2) match but (3) fails
    # - This forces the engine to try many positions
    
    # Create: char\nSPACE char\nSPACE char\nSPACE ...
    # Each position has char\n but lookahead sees space, not char
    print("Creating worst-case input...")
    text = "a\n " * 30000 + "b"
    print(f"Size: {len(text)} bytes ({len(text)/1024:.1f}KB)")
    
    start = time.time()
    result = cleaner._recover_punctuation(text)
    elapsed = time.time() - start
    print(f"Time: {elapsed:.4f}s")
    
    # Another worst case: almost-matches everywhere
    # char\nCHAR but CHAR is not in the class
    # But our class includes A-Za-z0-9 and CJK, so this is hard to break
    
    # What about CJK characters specifically?
    text = "字\n。" * 20000  # CJK char followed by CJK punctuation (not in class!)
    print(f"\nCJK with punctuation: {len(text)} bytes")
    start = time.time()
    result = cleaner._recover_punctuation(text)
    elapsed = time.time() - start
    print(f"Time: {elapsed:.4f}s")

if __name__ == "__main__":
    test_specific_ocr_pattern()
    analyze_actual_regex_behavior()
    test_pathological_cases()
    create_worst_case_input()
    print("\n=== Summary ===")
    print("None of the tests caused hanging.")
    print("The regex pattern appears to be well-behaved.")
    print("Need to investigate other potential causes...")
