"""Test script to reproduce the catastrophic backtracking issue."""

import time
import re
from src.data_processing.text_cleaner import TextCleaner, CleanerConfig


def test_recover_punctuation_performance():
    """Test _recover_punctuation with large OCR-like inputs."""
    cleaner = TextCleaner()
    
    # Simulate large OCR output - many lines of Chinese text
    print("Testing with increasing input sizes...")
    
    for multiplier in [100, 500, 1000, 2000, 5000]:
        # Create text that looks like OCR output with many short lines
        lines = ["天地玄黃宇宙洪荒" * 5] * multiplier
        text = "\n".join(lines)
        
        print(f"\nInput size: {len(text):,} chars, {multiplier} lines")
        
        start = time.time()
        try:
            result = cleaner.clean(text)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s")
            
            if elapsed > 5:
                print(f"  WARNING: Took longer than 5 seconds!")
            if elapsed > 30:
                print(f"  CRITICAL: Timeout threshold exceeded!")
                break
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")
            break


def test_regex_pattern_directly():
    """Test the regex pattern directly to isolate the issue."""
    print("\n\n=== Testing regex pattern directly ===")
    
    # The problematic pattern from _recover_punctuation
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    for multiplier in [100, 500, 1000, 2000, 5000, 10000]:
        lines = ["天地玄黃" * 5] * multiplier
        text = "\n".join(lines)
        
        print(f"\nInput size: {len(text):,} chars, {multiplier} lines")
        
        start = time.time()
        try:
            result = re.sub(pattern, r"\1.\n", text, flags=re.MULTILINE)
            elapsed = time.time() - start
            print(f"  re.sub completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")


def test_problematic_patterns():
    """Test various patterns that could cause backtracking."""
    print("\n\n=== Analyzing potential backtracking sources ===")
    
    # Test with text that has no newlines (worst case for some patterns)
    text_no_newlines = "天地玄黃" * 5000
    
    # Pattern 1: Current pattern (should be fine)
    pattern1 = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    # Pattern 2: What if there's a different problematic pattern?
    # Let's check the punct_patterns defined in __init__
    punct_patterns = {
        "period": re.compile(r"(?<=[一 - 龥])\.(?=[一 - 龥])"),
        "comma": re.compile(r"(?<=[一 - 龥]),(?=[一 - 龥])"),
        "colon": re.compile(r"(?<=[一 - 龥]):(?=[一 - 龥])"),
        "semicolon": re.compile(r"(?<=[一 - 龥]);(?=[一 - 龥])"),
        "question": re.compile(r"(?<=[一 - 龥])\?"),
        "exclaim": re.compile(r"(?<=[一 - 龥])!"),
    }
    
    print("\nTesting punct_patterns on text without punctuation:")
    for name, pattern in punct_patterns.items():
        start = time.time()
        result = pattern.sub("", text_no_newlines)
        elapsed = time.time() - start
        print(f"  {name}: {elapsed:.3f}s")
    
    # Now test with text that HAS punctuation-like characters
    text_with_dots = "天地。玄黃。宇宙。洪荒。" * 1000
    
    print("\nTesting punct_patterns on text with periods:")
    for name, pattern in punct_patterns.items():
        start = time.time()
        result = pattern.sub(".", text_with_dots)
        elapsed = time.time() - start
        print(f"  {name}: {elapsed:.3f}s")


def test_alternating_pattern():
    """Test with alternating character/newline patterns."""
    print("\n\n=== Testing alternating patterns (potential ReDoS) ===")
    
    # This creates a pattern where regex might backtrack heavily
    # Single char followed by newline repeatedly
    for n in [100, 500, 1000, 2000, 5000]:
        # Alternating single char and newline
        text = "".join([f"天\n" for _ in range(n)])
        
        pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
        
        print(f"\nAlternating pattern: {n} repetitions")
        start = time.time()
        try:
            result = re.sub(pattern, r"\1.\n", text, flags=re.MULTILINE)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("CATASTROPHIC BACKTRACKING INVESTIGATION")
    print("=" * 60)
    
    test_recover_punctuation_performance()
    test_regex_pattern_directly()
    test_problematic_patterns()
    test_alternating_pattern()
    
    print("\n" + "=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)
