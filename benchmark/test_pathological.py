"""Test with truly pathological inputs that trigger catastrophic backtracking."""

import re
import time
import signal


def test_split_sentences_pathological():
    """
    The pattern ((?:[.!?\s]*)+) has nested quantifiers.
    
    Catastrophic backtracking occurs when:
    1. The inner quantifier (\s*) can match varying amounts
    2. The outer quantifier ()+ tries different groupings
    3. The overall match fails at the end
    
    Key insight: We need punctuation followed by OPTIONAL whitespace
    where the regex engine tries many combinations.
    """
    print("=" * 60)
    print("TEST 1: _split_sentences Pathological Input")
    print("=" * 60)
    
    # The actual pattern from the buggy code
    pattern = r"((?:[.!?;]\s*)+)"
    
    # For catastrophic backtracking, we need:
    # - Many items that match the inner pattern
    # - A failure condition at the end
    # - Ambiguity in how to group the matches
    
    # Test 1: Alternating punctuation and non-whitespace
    # This creates ambiguity in grouping
    for n in [5, 10, 15, 20, 25, 30]:
        # Pattern like: 。x。x。x... where x is non-whitespace
        # The regex tries to match \s* as empty or not for each position
        text = "".join(["。x" for _ in range(n)])
        
        print(f"\nn={n}: {text[:40]}... ({len(text)} chars)")
        
        start = time.time()
        try:
            result = re.split(pattern, text)
            elapsed = time.time() - start
            print(f"  Time: {elapsed:.4f}s, Parts: {len(result)}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR: {e}")
    
    # Test 2: Punctuation with optional spaces - the real killer
    # Pattern: 。 。 。 ... (with single space between)
    # At the end, don't provide what the regex expects
    print("\n--- Test 2: Punctuation + Space sequences ---")
    for n in [10, 15, 20, 25, 30]:
        # Many punct+space, ending with something that breaks the pattern
        text = "。 " * n + "END"
        
        print(f"\nn={n}: ({len(text)} chars)")
        
        start = time.time()
        result = re.split(pattern, text)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.4f}s, Parts: {len(result)}")


def test_strip_annotations_pathological():
    """
    Pattern: [\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)
    
    The .*? with lookahead (?=[\[【]|$) causes the regex to:
    1. Match minimally with .*?
    2. Check lookahead at each position
    3. On long text without [/[ or end, this scans the entire string
    """
    print("\n" + "=" * 60)
    print("TEST 2: _strip_annotations Pathological Input")
    print("=" * 60)
    
    pattern = r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)"
    
    # Text with opening annotation but no closing bracket or new opening
    # Forces .*? to scan character by character to the end
    for n in [100, 500, 1000, 2000, 5000, 10000]:
        text = "[注]" + "天地玄黃宇宙洪荒" * n  # No closing bracket
        
        print(f"\nn={n}: ({len(text):,} chars)")
        
        start = time.time()
        result = re.sub(pattern, "", text)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.4f}s, Output: {len(result):,} chars")


def test_whitespace_pathological():
    """
    Pattern: \n\s*\n
    
    \s matches newlines, so on input like \n\n\n... 
    the regex engine tries different ways to match \s*
    """
    print("\n" + "=" * 60)
    print("TEST 3: _normalize_whitespace Pathological Input")
    print("=" * 60)
    
    pattern = r"\n\s*\n"
    
    # Many consecutive newlines
    for n in [10, 20, 30, 40, 50]:
        text = "start" + "\n" * n + "end"
        
        print(f"\nn={n}: ({len(text)} chars)")
        
        start = time.time()
        result = re.sub(pattern, "\n", text)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.4f}s")


def test_recover_punctuation_analysis():
    """
    Analyze if _recover_punctuation could ever hang.
    
    Pattern: ([一 - 龥 A-Za-z0-9])\n(?=[一 - 龥 A-Za-z0-9])
    
    This pattern is ACTUALLY SAFE because:
    1. Character class [...] matches exactly one char - no quantifier
    2. \n is literal - no ambiguity
    3. Lookahead (?=...) doesn't consume characters
    4. No nested quantifiers possible
    
    The task description mentions this hangs, but the current pattern
    cannot cause catastrophic backtracking.
    """
    print("\n" + "=" * 60)
    print("TEST 4: _recover_punctuation Analysis")
    print("=" * 60)
    
    pattern = r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
    
    print("\nPattern analysis:")
    print("  - First group: [\\u4e00-\\u9fffA-Za-z0-9] - single char class, NO quantifier")
    print("  - Literal: \\n - single newline")
    print("  - Lookahead: (?=...) - zero-width assertion")
    print("  - Conclusion: CANNOT cause catastrophic backtracking")
    
    # Verify with large input
    for n in [1000, 5000, 10000, 20000]:
        lines = ["天地玄黃"] * n
        text = "\n".join(lines)
        
        print(f"\nn={n}: ({len(text):,} chars)")
        
        start = time.time()
        result = re.sub(pattern, r"\1.\n", text, flags=re.MULTILINE)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.4f}s (linear scaling expected)")


def demonstrate_catastrophic_backtracking():
    """Demonstrate what actual catastrophic backtracking looks like."""
    print("\n" + "=" * 60)
    print("TEST 5: Demonstration of Real Catastrophic Backtracking")
    print("=" * 60)
    
    # Classic ReDoS pattern: (a+)+
    # On input like "aaaaaaaaaaaaaaaaaaaaX" (many a's, ending with X)
    # The regex tries 2^n ways to group the a's before failing
    
    pattern = r"(a+)+b"
    
    print("\nPattern: (a+)+b")
    print("This has nested quantifiers - outer ()+ and inner a+")
    print("On input 'aaa...X' (no trailing 'b'), it tries 2^n groupings\n")
    
    for n in [10, 15, 20, 22, 24, 25]:
        text = "a" * n + "X"  # No 'b' at the end - forces backtracking
        
        print(f"n={n}: ", end="", flush=True)
        
        start = time.time()
        
        # Use alarm for timeout
        def timeout_handler(signum, frame):
            raise TimeoutError("Timeout")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)
        
        try:
            result = re.search(pattern, text)
            signal.alarm(0)
            elapsed = time.time() - start
            signal.signal(signal.SIGALRM, old_handler)
            print(f"{elapsed:.4f}s - Match: {result}")
        except TimeoutError:
            elapsed = time.time() - start
            signal.signal(signal.SIGALRM, old_handler)
            print(f"TIMEOUT after {elapsed:.1f}s (CATASTROPHIC!)")
            break


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PATHOLOGICAL INPUT TESTING FOR CATASTROPHIC BACKTRACKING")
    print("=" * 70)
    
    test_split_sentences_pathological()
    test_strip_annotations_pathological()
    test_whitespace_pathological()
    test_recover_punctuation_analysis()
    demonstrate_catastrophic_backtracking()
    
    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)
