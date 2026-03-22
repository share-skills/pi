"""Test script to reproduce the catastrophic backtracking issue."""

import re
import time
from src.data_processing.text_cleaner import TextCleaner, CleanerConfig

# Test case 1: Large OCR output simulation (>10KB)
def generate_large_ocr_text(size_kb=15):
    """Generate simulated large OCR output with many lines."""
    base_text = "子曰學而時習之不亦說乎有朋自遠方來不亦樂乎人不知而不慍不亦君子乎"
    lines = []
    target_chars = size_kb * 1024
    
    while len("".join(lines)) < target_chars:
        # Simulate OCR output - lines without proper punctuation
        lines.append(base_text)
    
    return "\n".join(lines)


def test_recover_punctuation_performance():
    """Test the _recover_punctuation method with large inputs."""
    print("=" * 60)
    print("Testing _recover_punctuation performance")
    print("=" * 60)
    
    # Test with different sizes
    for size in [1, 5, 10, 15, 20]:
        text = generate_large_ocr_text(size_kb=size)
        print(f"\nTesting with {size}KB input ({len(text)} chars)...")
        
        cleaner = TextCleaner()
        start = time.time()
        
        try:
            result = cleaner._recover_punctuation(text)
            elapsed = time.time() - start
            print(f"  ✓ Completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ✗ Failed after {elapsed:.3f}s: {e}")
            
        # Timeout after 30 seconds
        if elapsed > 30:
            print(f"  ⚠ TIMEOUT - Taking too long!")
            break


def test_regex_patterns():
    """Test individual regex patterns for backtracking issues."""
    print("\n" + "=" * 60)
    print("Testing individual regex patterns")
    print("=" * 60)
    
    # The problematic pattern from _recover_punctuation
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    print(f"\nPattern: {pattern}")
    print("This pattern uses a lookahead which is generally safe,")
    print("but let's check for other issues...")
    
    # Test with pathological input
    # Create text that might cause issues: many consecutive short lines
    pathological = "\n".join(["a"] * 1000)
    
    start = time.time()
    result = re.sub(pattern, r"\1.\n", pathological, flags=re.MULTILINE)
    elapsed = time.time() - start
    print(f"Pathological test (1000 single-char lines): {elapsed:.3f}s")
    
    # Test with Chinese characters
    pathological_chinese = "\n".join(["子"] * 1000)
    start = time.time()
    result = re.sub(pattern, r"\1.\n", pathological_chinese, flags=re.MULTILINE)
    elapsed = time.time() - start
    print(f"Chinese pathological test: {elapsed:.3f}s")


def test_full_clean_pipeline():
    """Test the full clean pipeline with large inputs."""
    print("\n" + "=" * 60)
    print("Testing full clean() pipeline")
    print("=" * 60)
    
    text = generate_large_ocr_text(size_kb=10)
    print(f"\nInput size: {len(text)} chars")
    
    cleaner = TextCleaner()
    start = time.time()
    
    try:
        result = cleaner.clean(text)
        elapsed = time.time() - start
        print(f"Completed in {elapsed:.3f}s")
        print(f"Output size: {len(result)} chars")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed after {elapsed:.3f}s: {e}")


if __name__ == "__main__":
    test_regex_patterns()
    test_recover_punctuation_performance()
    test_full_clean_pipeline()
