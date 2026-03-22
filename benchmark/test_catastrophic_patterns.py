"""Test to identify potential catastrophic backtracking patterns in _recover_punctuation."""

import re
import time


def test_pattern_variants():
    """Test different regex pattern variants that could cause catastrophic backtracking."""
    
    print("=" * 70)
    print("Testing potential catastrophic backtracking patterns")
    print("=" * 70)
    
    # Common patterns that can cause catastrophic backtracking:
    # 1. Nested quantifiers: (a+)+, (a*)*, etc.
    # 2. Alternation with overlapping patterns: (a|aa)+
    # 3. Multiple lookahead/lookbehind combinations
    
    # Test case 1: Pattern with nested quantifiers (BAD)
    bad_pattern_1 = r"([一 - 龥]+)+\n"
    text_1 = "子" * 100 + "\n" + "子" * 100
    print(f"\n1. Nested quantifiers pattern: {bad_pattern_1}")
    start = time.time()
    try:
        result = re.sub(bad_pattern_1, "", text_1)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 2: Pattern with multiple lookaheads (can be slow)
    bad_pattern_2 = r"(?=[一 - 龥])([一 - 龥]*[一 - 龥])\n(?=[一 - 龥])"
    text_2 = "\n".join(["子" * 50] * 100)
    print(f"\n2. Multiple lookahead pattern: {bad_pattern_2}")
    start = time.time()
    try:
        result = re.sub(bad_pattern_2, "", text_2)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 3: Greedy match with backtracking opportunity
    bad_pattern_3 = r".*\n.*"
    text_3 = "\n".join(["子曰"] * 500)
    print(f"\n3. Greedy multiline pattern: {bad_pattern_3}")
    start = time.time()
    try:
        result = re.findall(bad_pattern_3, text_3, re.MULTILINE)
        print(f"   Time: {time.time() - start:.4f}s, matches: {len(result)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 4: Non-greedy with many opportunities to backtrack
    bad_pattern_4 = r"(.*?)\n(.*?)"
    text_4 = "\n".join(["test line " + str(i) for i in range(500)])
    print(f"\n4. Non-greedy pair pattern: {bad_pattern_4}")
    start = time.time()
    try:
        result = re.findall(bad_pattern_4, text_4)
        print(f"   Time: {time.time() - start:.4f}s, matches: {len(result)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 5: Character class with overlapping ranges (potential issue)
    bad_pattern_5 = r"([a-zA-Z0-9 一 - 龥]+)\n([a-zA-Z0-9 一 - 龥]+)"
    text_5 = "\n".join(["Line" + str(i) + "行" for i in range(1000)])
    print(f"\n5. Overlapping character class: {bad_pattern_5}")
    start = time.time()
    try:
        result = re.sub(bad_pattern_5, r"\1.\n\2", text_5)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 6: Complex lookahead/lookbehind combination
    bad_pattern_6 = r"(?<=[一 - 龥])(?=\n)(?=\n[一 - 龥])"
    text_6 = "\n\n".join(["子曰學而時習之"] * 100)
    print(f"\n6. Complex lookahead/lookbehind: {bad_pattern_6}")
    start = time.time()
    try:
        result = re.sub(bad_pattern_6, ".", text_6)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 7: The CURRENT pattern (should be fast)
    current_pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    text_7 = "\n".join(["Line" + str(i) + "行" for i in range(5000)])
    print(f"\n7. CURRENT pattern (should be fast): {current_pattern}")
    start = time.time()
    try:
        result = re.sub(current_pattern, r"\1.\n", text_7)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test case 8: Pattern with repeated character classes causing backtracking
    bad_pattern_8 = r"(([一 - 龥]|[a-zA-Z])+)\n"
    text_8 = "\n".join(["abc 子 def 行 ghi 子" for _ in range(500)])
    print(f"\n8. Alternation in capture group: {bad_pattern_8}")
    start = time.time()
    try:
        result = re.sub(bad_pattern_8, r"\1.\n", text_8)
        print(f"   Time: {time.time() - start:.4f}s")
    except Exception as e:
        print(f"   Error: {e}")


def simulate_original_bug():
    """Try to simulate what the original bug might have been."""
    print("\n" + "=" * 70)
    print("Simulating potential original bug scenarios")
    print("=" * 70)
    
    from src.data_processing.text_cleaner import TextCleaner
    
    # Scenario 1: Very long text with specific structure
    # Many short lines alternating between Chinese and ASCII
    scenario_1 = "\n".join([f"Line{i}子{i}" for i in range(10000)])
    print(f"\nScenario 1: {len(scenario_1)} chars, 10000 mixed lines")
    cleaner = TextCleaner()
    start = time.time()
    result = cleaner._recover_punctuation(scenario_1)
    elapsed = time.time() - start
    print(f"   Time: {elapsed:.4f}s")
    
    # Scenario 2: Text with no newlines (single long line)
    scenario_2 = "子" * 100000
    print(f"\nScenario 2: Single line with {len(scenario_2)} chars")
    start = time.time()
    result = cleaner._recover_punctuation(scenario_2)
    elapsed = time.time() - start
    print(f"   Time: {elapsed:.4f}s")
    
    # Scenario 3: Many consecutive newlines
    scenario_3 = "text" + "\n" * 5000 + "end"
    print(f"\nScenario 3: Text with 5000 consecutive newlines")
    start = time.time()
    result = cleaner._recover_punctuation(scenario_3)
    elapsed = time.time() - start
    print(f"   Time: {elapsed:.4f}s")
    
    # Scenario 4: Real OCR-like output (sentences on separate lines)
    sentences = [
        "子曰學而時習之不亦說乎",
        "有朋自遠方來不亦樂乎",
        "人不知而不慍不亦君子乎",
        "其為人也孝弟",
        "君子務本本立而道生",
    ]
    scenario_4 = "\n".join(sentences * 2000)  # Repeat many times
    print(f"\nScenario 4: OCR-like output, {len(scenario_4)} chars")
    start = time.time()
    result = cleaner._recover_punctuation(scenario_4)
    elapsed = time.time() - start
    print(f"   Time: {elapsed:.4f}s")


if __name__ == "__main__":
    test_pattern_variants()
    simulate_original_bug()
