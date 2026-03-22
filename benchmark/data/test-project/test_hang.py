"""Test script to reproduce the hanging issue with _recover_punctuation."""

#!/usr/bin/env python3
import sys
import time
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/src')

from data_processing.text_cleaner import TextCleaner

# Create a large OCR-like text that triggers the hang
# The issue is with texts > 10KB
def create_problematic_text(size_kb=15):
    """Create text that may cause catastrophic backtracking."""
    # Pattern: many Chinese characters with newlines between them
    # This creates input that the regex needs to process
    base = "學而時習之不亦說乎有朋自遠方來"
    repetitions = (size_kb * 1024) // len(base) + 1
    text = "\n".join([base[i:i+1] for i in range(len(base) * repetitions)])
    return text[:size_kb * 1024]

def create_problematic_text_v2(size_kb=15):
    """Create text with alternating patterns that can cause backtracking."""
    # Many single chars separated by newlines
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    text = "\n".join(chars * (size_kb * 50))
    return text

def test_recover_punctuation():
    cleaner = TextCleaner()
    
    print("Creating test text (~15KB)...")
    test_text = create_problematic_text_v2(15)
    print(f"Text length: {len(test_text)} bytes")
    
    print("Calling _recover_punctuation...")
    start = time.time()
    
    try:
        result = cleaner._recover_punctuation(test_text)
        elapsed = time.time() - start
        print(f"Completed in {elapsed:.2f} seconds")
        print(f"Result length: {len(result)}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Error after {elapsed:.2f} seconds: {e}")

if __name__ == "__main__":
    test_recover_punctuation()
