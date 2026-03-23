"""Test the BUGGY version from test-project to reproduce catastrophic backtracking."""

import sys
import time
import re

# Import from the BUGGY version
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project')
from src.data_processing.text_cleaner import TextCleaner


def test_split_sentences_backtracking():
    """Test _split_sentences with pathological inputs."""
    print("=" * 60)
    print("TEST 1: _split_sentences Catastrophic Backtracking")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    # The pattern: ((?:[.!?;]\s*)+)
    # Nested quantifiers: outer ()+ and inner \s*
    # Triggers on: many punctuation marks followed by whitespace
    
    for n in [10, 20, 30, 40, 50]:
        # Create text with many punctuation marks and spaces
        # This should trigger exponential backtracking
        text = "".join(["。" * n + " " * n])
        
        print(f"\nInput: {n} punctuation marks + {n} spaces ({len(text)} chars)")
        
        start = time.time()
        try:
            # Set alarm for timeout (Unix only)
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Timeout after 10s")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            result = cleaner._split_sentences(text)
            signal.alarm(0)  # Cancel alarm
            signal.signal(signal.SIGALRM, old_handler)
            
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s - {len(result)} parts")
            
            if elapsed > 5:
                print(f"  WARNING: Took longer than 5 seconds!")
                
        except TimeoutError as e:
            elapsed = time.time() - start
            print(f"  TIMEOUT after {elapsed:.1f}s - CATASTROPHIC BACKTRACKING DETECTED!")
            break
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")
            break


def test_strip_annotations_backtracking():
    """Test _strip_annotations with pathological inputs."""
    print("\n" + "=" * 60)
    print("TEST 2: _strip_annotations Backtracking Risk")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    # Pattern: [\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)
    # Non-greedy .*? with lookahead at end can cause backtracking
    # on long annotations without closing brackets
    
    for n in [100, 500, 1000, 2000, 5000]:
        # Create text with unclosed annotation followed by lots of content
        text = "[注]" + "天地玄黃" * n
        
        print(f"\nInput: Unclosed annotation + {n} repetitions ({len(text):,} chars)")
        
        start = time.time()
        try:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Timeout after 10s")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            result = cleaner._strip_annotations(text)
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s - output length: {len(result):,}")
            
            if elapsed > 5:
                print(f"  WARNING: Took longer than 5 seconds!")
                
        except TimeoutError as e:
            elapsed = time.time() - start
            print(f"  TIMEOUT after {elapsed:.1f}s!")
            break
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")
            break


def test_normalize_whitespace_issue():
    """Test _normalize_whitespace with problematic inputs."""
    print("\n" + "=" * 60)
    print("TEST 3: _normalize_whitespace Analysis")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    # Pattern: \n\s*\n
    # \s can match newlines, which could cause issues with multiple consecutive newlines
    
    for n in [10, 50, 100, 200]:
        # Many consecutive newlines with spaces
        text = "段落 1" + ("\n " * n) + "\n段落 2"
        
        print(f"\nInput: {n} newline-space pairs ({len(text)} chars)")
        
        start = time.time()
        try:
            result = cleaner._normalize_whitespace(text)
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")


def test_full_clean_performance():
    """Test full clean() method with large OCR-like input."""
    print("\n" + "=" * 60)
    print("TEST 4: Full clean() Performance on Large Input")
    print("=" * 60)
    
    cleaner = TextCleaner()
    
    for multiplier in [100, 500, 1000, 2000]:
        # Simulate OCR output with many short lines
        lines = ["天地玄黃宇宙洪荒" * 3] * multiplier
        text = "\n".join(lines)
        
        print(f"\nInput: {multiplier} lines ({len(text):,} chars)")
        
        start = time.time()
        try:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Timeout after 30s")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            result = cleaner.clean(text)
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            
            elapsed = time.time() - start
            print(f"  Completed in {elapsed:.3f}s")
            
            if elapsed > 10:
                print(f"  WARNING: Performance issue detected!")
                
        except TimeoutError as e:
            elapsed = time.time() - start
            print(f"  TIMEOUT after {elapsed:.1f}s - HANG DETECTED!")
            break
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.3f}s: {e}")
            break


def analyze_regex_patterns():
    """Analyze all regex patterns for backtracking risk."""
    print("\n" + "=" * 60)
    print("TEST 5: Regex Pattern Analysis")
    print("=" * 60)
    
    patterns = {
        "_split_sentences": r"((?:[.!?;]\s*)+)",
        "_strip_annotations (pattern 1)": r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)",
        "_strip_annotations (pattern 2)": r"（按 [：:].*?）",
        "_normalize_whitespace (pattern 1)": r"[ \t]+",
        "_normalize_whitespace (pattern 2)": r"\n\s*\n",
        "_normalize_whitespace (pattern 3)": r" *\n *",
        "_recover_punctuation": r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])",
    }
    
    print("\nBacktracking Risk Analysis:")
    print("-" * 60)
    
    for name, pattern in patterns.items():
        risks = []
        
        # Check for nested quantifiers
        if re.search(r'\([^)]*[\*\+][^)]*\)[\*\+]', pattern):
            risks.append("NESTED QUANTIFIERS")
        
        # Check for non-greedy with anchor/lookahead
        if '.*?' in pattern and ('(?=' in pattern or '$)' in pattern):
            risks.append("NON-GREEDY + LOOKAHEAD/ANCHOR")
        
        # Check for \s that could match newlines unexpectedly
        if '\\s' in pattern:
            risks.append("\\s MATCHES NEWLINES")
        
        # Check for overlapping alternations
        if re.search(r'\[.*\].*\[.*\]', pattern) and '|' in pattern:
            risks.append("POTENTIAL OVERLAP")
        
        risk_level = "HIGH" if len(risks) >= 2 else "MEDIUM" if len(risks) == 1 else "LOW"
        
        print(f"{name}:")
        print(f"  Pattern: {pattern}")
        print(f"  Risks: {', '.join(risks) if risks else 'None detected'}")
        print(f"  Risk Level: {risk_level}")
        print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("CATASTROPHIC BACKTRACKING INVESTIGATION - BUGGY VERSION")
    print("Source: data/test-project/src/data_processing/text_cleaner.py")
    print("=" * 70)
    
    analyze_regex_patterns()
    test_split_sentences_backtracking()
    test_strip_annotations_backtracking()
    test_normalize_whitespace_issue()
    test_full_clean_performance()
    
    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETE")
    print("=" * 70)
