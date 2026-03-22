#!/usr/bin/env python3
"""Deep dive into catastrophic backtracking scenarios."""

import re
import time

def test_whitespace_pattern():
    """Test _normalize_whitespace patterns."""
    print("=== Testing _normalize_whitespace ===")
    
    # Pattern: r"\n\s*\n" - this CAN cause issues!
    # \s* is greedy and can match newlines
    # On input like: \n\n\n\n\n...\n (many newlines)
    # The pattern \n\s*\n has overlapping matches
    
    text = "\n" * 10000
    start = time.time()
    result = re.sub(r"\n\s*\n", "\n", text)
    print(f"10K newlines: {time.time() - start:.4f}s")
    
    text = "\n" * 50000
    start = time.time()
    result = re.sub(r"\n\s*\n", "\n", text)
    print(f"50K newlines: {time.time() - start:.4f}s")
    
    # Worse case: mixed whitespace
    text = ("\n \n\t\n  \n") * 5000
    start = time.time()
    result = re.sub(r"\n\s*\n", "\n", text)
    print(f"Mixed whitespace 5K groups: {time.time() - start:.4f}s")

def test_dedup_pattern():
    """Test _split_sentences pattern."""
    print("\n=== Testing _split_sentences ===")
    
    # Pattern: r"((?:[。！？；]\s*)+)"
    # This has nested quantifiers: (?:...)+ with \s* inside
    # But the inner \s* is followed by end of group, not another quantifier
    
    # Worst case: many punctuation marks with varying whitespace
    text = ("。 " * 1000 + "!") * 10
    start = time.time()
    result = re.split(r"((?:[。！？；]\s*)+)", text)
    print(f"10K punct with spaces: {time.time() - start:.4f}s")
    
    # More pathological: punctuation with no spaces between
    text = "。！？；" * 2000
    start = time.time()
    result = re.split(r"((?:[。！？；]\s*)+)", text)
    print(f"8K consecutive punct: {time.time() - start:.4f}s")

def test_recovery_pattern_more_carefully():
    """Test the recovery pattern with specific pathological inputs."""
    print("\n=== Testing _recover_punctuation deeply ===")
    
    # Pattern: r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    # 
    # Catastrophic backtracking requires:
    # 1. Nested quantifiers OR
    # 2. Alternations with overlapping possibilities OR  
    # 3. Atomic grouping issues
    #
    # This pattern has NONE of these. It's O(n).
    #
    # BUT WAIT - let me check if there's an issue with MULTILINE flag
    # and very long lines without newlines...
    
    # Actually, let's test what happens with NO newlines but lots of chars
    text = "字" * 100000
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    start = time.time()
    result = re.sub(pattern, r"\1.\n", text, flags=re.MULTILINE)
    print(f"100K chars, no newlines: {time.time() - start:.4f}s")
    
    # What about alternating char/newline where lookahead always fails?
    text = "a\nb\nc\nd\ne\n" * 5000
    start = time.time()
    result = re.sub(pattern, r"\1.\n", text, flags=re.MULTILINE)
    print(f"25K char-newline pairs: {time.time() - start:.4f}s")

def find_real_culprit():
    """Search for patterns that could actually hang."""
    print("\n=== Searching for real culprit ===")
    
    # Looking at the code again...
    # Wait, I need to check if there's interaction BETWEEN patterns
    # when applied sequentially
    
    # Also need to check the actual reported symptom:
    # "_recover_punctuation method never returns for texts >10KB"
    
    # Let me create realistic OCR output
    print("\nCreating realistic large OCR output...")
    
    # Simulate OCR output: many short lines, some with trailing spaces
    # mixed encoding artifacts, etc.
    lines = []
    for i in range(3000):
        line = f"第{i}章詩經國風周南關關雎鳩在河之洲窈窕淑女君子好逑"
        if i % 10 == 0:
            line += "   \t  "  # Trailing whitespace
        if i % 7 == 0:
            line += "\ufeff"  # BOM
        lines.append(line)
    
    text = "\n".join(lines)
    print(f"Text size: {len(text)} bytes")
    
    import sys
    sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')
    from data_processing.text_cleaner import TextCleaner
    cleaner = TextCleaner()
    
    # Test just _recover_punctuation
    start = time.time()
    result = cleaner._recover_punctuation(text)
    elapsed = time.time() - start
    print(f"_recover_punctuation took: {elapsed:.4f}s")
    
    # Test full clean pipeline
    start = time.time()
    result = cleaner.clean(text)
    elapsed = time.time() - start
    print(f"Full clean() took: {elapsed:.4f}s")

def test_annotation_pattern_pathological():
    """Test annotation pattern with worst-case input."""
    print("\n=== Testing annotation pattern pathology ===")
    
    # Pattern: r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)"
    # 
    # This is potentially problematic because:
    # 1. .*? scans character by character (non-greedy)
    # 2. At each position, checks lookahead (?=[\[【]|$)
    # 3. If text has no [【 until end, scans ENTIRE remaining text
    # 4. With multiple [注] markers, rescans from each one
    
    # Create text with many opening markers but no closing
    text = "[注]" + "x" * 500 + "[注]" + "x" * 500 + "[注]" + "x" * 500
    start = time.time()
    result = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)
    print(f"3 markers, 1.5K chars: {time.time() - start:.4f}s")
    
    text = "[注]" + "x" * 5000 + "[注]" + "x" * 5000 + "[注]" + "x" * 5000
    start = time.time()
    result = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)
    print(f"3 markers, 15K chars: {time.time() - start:.4f}s")
    
    # Many markers
    text = "".join(["[注]" + "x" * 100 for _ in range(100)])
    start = time.time()
    result = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)
    print(f"100 markers, 10K chars: {time.time() - start:.4f}s")

if __name__ == "__main__":
    test_whitespace_pattern()
    test_dedup_pattern()
    test_recovery_pattern_more_carefully()
    find_real_culprit()
    test_annotation_pattern_pathological()
