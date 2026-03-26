#!/usr/bin/env python3
"""Comprehensive code review tests for quality_filter.py"""
import sys
sys.path.insert(0, 'src')

from data_engineering.quality_filter import QualityFilter, FilterConfig, PerplexityScorer

print("=" * 70)
print("COMPREHENSIVE CODE REVIEW - QUALITY FILTER")
print("=" * 70)

issues_found = []
hidden_issues = []

# =============================================================================
# CRITICAL BUGS
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 1: CRITICAL BUGS")
print("=" * 70)

# Issue 1.1: Division by Zero in PerplexityScorer.train()
print("\n[Issue 1.1] Division by Zero Risk in train()")
try:
    scorer = PerplexityScorer()
    # Train with text that has Chinese chars but after filtering might cause issues
    scorer.train(["測試"])  # 2 Chinese chars
    # Now check internal state - unigram_probs should have entries
    print(f"  After training on '測試': unigram_probs has {len(scorer._unigram_probs)} entries")
    
    # The REAL bug: when total_chars is 0, the loop for unigram_probs never runs
    # But if we have SOME Chinese chars and then score non-Chinese text...
    score = scorer.score("hello")  # No Chinese chars
    print(f"  Score for 'hello' (no Chinese): {score}")
    # This returns inf because chars list is empty - handled correctly
    
    # BUT the division by zero happens when:
    # - We train on text with ONLY Chinese chars
    # - Then try to compute unigram probs when total_chars could be problematic
    # Actually looking at line 91: self._unigram_probs[char] = count / total_chars
    # This WILL divide by zero if total_chars is 0 AND there are unigram counts
    # But if total_chars is 0, unigram_counts would also be empty...
    # Let me trace through more carefully
    
    # ACTUAL BUG SCENARIO: Empty reference list
    scorer2 = PerplexityScorer()
    scorer2.train([])  # Empty list!
    print(f"  Trained on empty list, _trained={scorer2._trained}")
    # With empty list, total_chars=0, unigram_counts={}, vocab_size=0
    # The for loops don't run, so no division by zero occurs
    # But _trained is still set to True!
    
except ZeroDivisionError as e:
    print(f"  CAUGHT ZeroDivisionError: {e}")
    issues_found.append("1.1: Division by zero in train()")
except Exception as e:
    print(f"  Exception: {type(e).__name__}: {e}")

# Issue 1.2: Dedup removes ALL duplicates including the first occurrence
print("\n[Issue 1.2] Dedup Logic Error - First item passes but second blocked")
qf = QualityFilter()
sample1 = {"instruction": "test", "output": "hello world output"}
sample2 = {"instruction": "test", "output": "hello world output"}
result = qf.filter([sample1, sample2])
print(f"  Input: 2 identical samples")
print(f"  Output: {len(result)} samples")
if len(result) == 1:
    print("  EXPECTED: First passes, second deduped -> 1 result")
    print("  Wait, we got 1? Let me check the logic again...")
elif len(result) == 0:
    print("  BUG: Both filtered! The dedup adds to seen_hashes AFTER checking,")
    print("       so first passes check, gets added. Second sees it in hash, blocked.")
    print("       But filter() only appends if _passes_all_checks returns True...")
    print("       So first SHOULD pass... unless something else filters it")
    issues_found.append("1.2: Dedup may not work as expected")

# Let me trace through more carefully
print("\n  Tracing dedup logic:")
qf2 = QualityFilter()
s1 = {"instruction": "same", "output": "output"}
print(f"  Sample 1 instruction: '{s1['instruction']}'")
print(f"  Sample 2 instruction: '{s1['instruction']}' (identical)")

# Check each filter individually
print(f"  _check_length(s1): {qf2._check_length(s1)}")
print(f"  _check_language(s1): {qf2._check_language(s1)}")
print(f"  _check_content(s1): {qf2._check_content(s1)}")
print(f"  _check_dedup(s1) FIRST call: {qf2._check_dedup(s1)}")
print(f"  _check_dedup(s1) SECOND call: {qf2._check_dedup(s1)}")

# Ah! The issue is that _check_dedup returns True first time (not in hash yet)
# Then adds to hash. Second call returns False (already in hash).
# So first sample PASSES, second FAILS. Result should be 1.
# But we got 0 earlier... let me re-run

qf3 = QualityFilter()
samples = [
    {"instruction": "test", "output": "hello world this is a valid output"},
    {"instruction": "test", "output": "hello world this is a valid output"},
]
result = qf3.filter(samples)
print(f"\n  Re-test with longer output: {len(result)} passed")
if len(result) == 1:
    print("  OK: Dedup working correctly - first passes, second blocked")
elif len(result) == 0:
    print("  BUG: Something else is filtering both samples")
    print(f"  Stats: {qf3._stats}")

# =============================================================================
# LOGIC BUGS
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 2: LOGIC BUGS")
print("=" * 70)

# Issue 2.1: Whitespace sensitivity in dedup
print("\n[Issue 2.1] Whitespace Sensitivity in Dedup")
qf4 = QualityFilter()
s1 = {"instruction": "test ", "output": "output"}   # trailing space
s2 = {"instruction": "test", "output": "output"}    # no space
result = qf4.filter([s1, s2])
print(f"  Samples differ only by trailing space in instruction")
print(f"  Result: {len(result)} passed")
if len(result) == 2:
    print("  ISSUE: Near-duplicates NOT caught due to whitespace")
    hidden_issues.append("2.1: Whitespace-sensitive dedup allows near-duplicates")

# Issue 2.2: Language check doesn't handle instruction field properly
print("\n[Issue 2.2] Language Check Field Order")
qf5 = QualityFilter()
# What if instruction is English but output is Chinese?
sample = {"instruction": "Translate to English", "output": "這是一個中文輸出"}
result = qf5.filter([sample])
print(f"  English instruction + Chinese output")
print(f"  Result: {len(result)} passed")
ratio = sum(1 for c in (sample["output"] + sample["instruction"]) if "\u4e00" <= c <= "\u9fff")
total = len((sample["output"] + sample["instruction"]).replace(" ", "").replace("\n", ""))
print(f"  Chinese ratio: {ratio}/{total} = {ratio/total if total > 0 else 0:.2f}")

# Issue 2.3: Repetition ratio calculation edge case
print("\n[Issue 2.3] Repetition Ratio Edge Case")
qf6 = QualityFilter()
# Text with exactly 10 chars
text_10 = "abcdefghij"
text_9 = "abcdefghi"
ratio_10 = qf6._repetition_ratio(text_10)
ratio_9 = qf6._repetition_ratio(text_9)
print(f"  10-char text '{text_10}': ratio = {ratio_10}")
print(f"  9-char text '{text_9}': ratio = {ratio_9} (returns 0.0 immediately)")
print(f"  ISSUE: Sharp cutoff at 10 chars - 9 char text always passes repetition check")
hidden_issues.append("2.3: Sharp cutoff in repetition ratio at 10 chars")

# Issue 2.4: Banned patterns only check output, not instruction
print("\n[Issue 2.4] Banned Patterns Only Check Output Field")
qf7 = QualityFilter()
sample = {
    "instruction": "As an AI, explain...",  # Has banned pattern
    "output": "This is a normal response"
}
result = qf7._check_content(sample)
print(f"  Instruction has 'As an AI', output is clean")
print(f"  _check_content result: {result} (True = passes)")
if result:
    print("  BUG: Banned pattern in instruction NOT detected!")
    hidden_issues.append("2.4: Banned patterns only checked in output field")

# =============================================================================
# CODE QUALITY ISSUES
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 3: CODE QUALITY ISSUES")
print("=" * 70)

# Issue 3.1: Unused numpy import
print("\n[Issue 3.1] Unused Import")
print("  File has: import numpy as np")
print("  But numpy is NEVER used anywhere in the file")
print("  IMPACT: Unnecessary dependency, slower imports")
issues_found.append("3.1: Unused numpy import")

# Issue 3.2: Missing return type annotations
print("\n[Issue 3.2] Missing Return Type Annotations")
import inspect
sig = inspect.signature(PerplexityScorer.train)
print(f"  PerplexityScorer.train signature: {sig}")
print("  Missing '-> None' return type annotation")
issues_found.append("3.2: Missing return type on train()")

# Issue 3.3: Accessing private attributes across classes
print("\n[Issue 3.3] Private Attribute Access")
print("  Line 197: if self._scorer._trained and not self._check_perplexity(sample)")
print("  QualityFilter accesses PerplexityScorer._trained directly")
print("  VIOLATION: Breaking encapsulation - should use property or method")
issues_found.append("3.3: Accessing private _trained attribute")

# Issue 3.4: Misleading variable name 'text_hash'
print("\n[Issue 3.4] Misleading Variable Name")
print("  Line 263: text_hash = dedup_text.strip()")
print("  This is NOT a hash - it's just the raw text stripped")
print("  MISLEADING: Should be 'dedup_key' or 'normalized_text'")
hidden_issues.append("3.4: Misleading variable name 'text_hash'")

# Issue 3.5: No actual hashing for dedup
print("\n[Issue 3.5] No Hash Function for Dedup")
print("  Uses raw text as dictionary key instead of hash")
print("  ISSUE: Memory inefficient for long texts, no collision protection")
hidden_issues.append("3.5: No hash function used for deduplication")

# Issue 3.6: Unused type imports
print("\n[Issue 3.6] Unused Type Imports")
print("  File imports: Optional, Tuple")
print("  But neither is used in any type annotation")
hidden_issues.append("3.6: Unused Optional and Tuple imports")

# =============================================================================
# EDGE CASES & VULNERABILITIES
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 4: EDGE CASES & VULNERABILITIES")
print("=" * 70)

# Issue 4.1: Empty input handling
print("\n[Issue 4.1] Empty Input List")
qf8 = QualityFilter()
result = qf8.filter([])
print(f"  filter([]) returns: {result}")
print(f"  Stats after empty filter: {qf8.get_stats()}")
if qf8.get_stats()["total_input"] == 0:
    print("  OK: Handles empty input correctly")

# Issue 4.2: Missing keys in sample
print("\n[Issue 4.2] Missing Keys in Sample Dict")
qf9 = QualityFilter()
sample_no_output = {"instruction": "test"}  # No output key
result = qf9.filter([sample_no_output])
print(f"  Sample without 'output' key: {len(result)} passed")
print(f"  Stats: {qf9._stats}")
# .get() returns None or default, so this should be handled gracefully
# But what does it get filtered on?

# Issue 4.3: Very long texts
print("\n[Issue 4.3] Very Long Text Handling")
qf10 = QualityFilter()
long_sample = {
    "instruction": "test",
    "output": "a" * 5000  # Exceeds max_length
}
result = qf10.filter([long_sample])
print(f"  5000-char output: {len(result)} passed (should be 0)")
if len(result) == 0:
    print("  OK: Correctly filtered by length check")

# Issue 4.4: Unicode edge cases
print("\n[Issue 4.4] Unicode Edge Cases")
qf11 = QualityFilter()
# Emoji and special characters
emoji_sample = {
    "instruction": "test",
    "output": "Hello 👋 World 🌍! This has emojis."
}
result = qf11.filter([emoji_sample])
chinese_count = sum(1 for c in emoji_sample["output"] if "\u4e00" <= c <= "\u9fff")
print(f"  Emoji text Chinese char count: {chinese_count}")
print(f"  Result: {len(result)} passed")
# Emojis are outside CJK range, so they count as non-Chinese

# Issue 4.5: Perplexity model trained on single character
print("\n[Issue 4.5] Perplexity Model Edge Case")
scorer3 = PerplexityScorer()
scorer3.train(["一"])  # Single Chinese char
print(f"  Trained on single char")
# Bigrams need at least 2 chars, so no bigrams will be created
print(f"  Bigram probs size: {len(scorer3._bigram_probs)}")
print(f"  Unigram probs size: {len(scorer3._unigram_probs)}")
# Scoring will use default 1e-6 for all bigrams
score = scorer3.score("一二")
print(f"  Score for '一二': {score}")

# Issue 4.6: State leakage between filter instances
print("\n[Issue 4.6] State Leakage Test")
qf_a = QualityFilter()
qf_b = QualityFilter()
sample = {"instruction": "test", "output": "valid output here"}
qf_a.filter([sample])
# qf_b should have independent state
result_b = qf_b.filter([sample])
print(f"  qf_a processed sample, qf_b processes same sample")
print(f"  qf_b result: {len(result_b)} passed")
if len(result_b) == 1:
    print("  OK: Independent instances")
else:
    print("  BUG: State shared between instances!")

# =============================================================================
# PERFORMANCE ISSUES
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 5: PERFORMANCE ISSUES")
print("=" * 70)

# Issue 5.1: O(n²) n-gram generation
print("\n[Issue 5.1] N-gram Generation Memory")
print("  Line 278: ngrams = [text[i:i + ngram_size] for i in range(...)]")
print("  Creates full list in memory instead of using generator")
print("  ISSUE: For 4096-char text, creates ~4092 4-gram strings")
hidden_issues.append("5.1: Inefficient n-gram list comprehension")

# Issue 5.2: Compiled patterns recreated per instance
print("\n[Issue 5.2] Pattern Compilation")
print("  Line 142-144: Patterns compiled in __init__")
print("  Each QualityFilter instance compiles all patterns")
print("  BETTER: Use class-level cached compilation")
hidden_issues.append("5.2: No caching of compiled regex patterns")

# Issue 5.3: No batch processing
print("\n[Issue 5.3] Sequential Processing Only")
print("  filter() processes one sample at a time in a loop")
print("  No vectorization or parallelization possible")
hidden_issues.append("5.3: No batch processing optimization")

# =============================================================================
# DOCUMENTATION ISSUES
# =============================================================================

print("\n" + "=" * 70)
print("SECTION 6: DOCUMENTATION ISSUES")
print("=" * 70)

# Issue 6.1: Docstring example doesn't match reality
print("\n[Issue 6.1] Docstring Example Accuracy")
print("  Line 133-135 shows example usage")
print("  But doesn't mention perplexity model needs training first")
print("  MISLEADING: Users might expect PPL filtering out of box")
hidden_issues.append("6.1: Incomplete docstring example")

# Issue 6.2: No documentation for stats dict keys
print("\n[Issue 6.2] Undocumented Stats Keys")
print("  _stats dict has keys but they're not documented")
print("  Users must read source to know available metrics")
hidden_issues.append("6.2: Stats dict keys not documented")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"\nConfirmed Issues Found: {len(issues_found)}")
for issue in issues_found:
    print(f"  - {issue}")

print(f"\nHidden Issues Discovered: {len(hidden_issues)}")
for issue in hidden_issues:
    print(f"  - {issue}")

print(f"\nTotal Issues: {len(issues_found) + len(hidden_issues)}")

print("\n" + "=" * 70)
print("REVIEW COMPLETE")
print("=" * 70)
