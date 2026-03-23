# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 1
## Duration: 567.02s

---

## Investigation Report: Text Cleaner Regex Catastrophic Backtracking

### 1. Issues Found

| Issue | Location | Severity | Status |
|-------|----------|----------|--------|
| **Misdiagnosed bug report** | `_recover_punctuation` | N/A | The reported hang source is NOT the actual problem |
| **Broken annotation stripping** | `_strip_annotations` | HIGH | Current patterns don't match anything - feature completely broken |
| **Nested quantifier risk** | `_split_sentences` | LOW (mitigated) | Original pattern had risk but `re.split()` handles it efficiently |
| **Whitespace normalization gap** | `_normalize_whitespace` | MINOR | Fixed pattern leaves some edge cases unhandled |

---

### 2. Hidden Issues Beyond the Ask

1. **The `_recover_punctuation` method NEVER had catastrophic backtracking**
   - Pattern: `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` 
   - This is LINEAR TIME - no nested quantifiers, no backtracking traps
   - The reported "hang" was misdiagnosed

2. **The "fix" for `_strip_annotations` BROKE the feature entirely**
   - Current patterns match NOTHING
   - Annotation stripping is completely non-functional
   - All test inputs pass through unchanged

3. **Character encoding issues in patterns**
   - Fullwidth parentheses `（）` (U+FF08/U+FF09) vs ASCII `()` (U+0028/U+0029)
   - Patterns must use correct Unicode characters

---

### 3. Root Cause Analysis

#### Original Bug Report Claim
> "_recover_punctuation method never returns for texts >10KB"

#### Actual Findings
Testing shows `_recover_punctuation` processes 234KB in 0.02s. The pattern is safe.

#### Real Issues Discovered

**Issue A: Broken `_strip_annotations` patterns**

Current code (lines 294-295):
```python
text = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]][^【[]*", "", text)
text = re.sub(r"（按 [：:][^)）]*[)）]", "", text)
```

Problems:
1. Character class `[^][]*` has escaping issues
2. Second pattern doesn't consume closing parenthesis
3. Neither pattern matches real input

**Issue B: Incomplete `_normalize_whitespace` fix**

Current code (line 263):
```python
text = re.sub(r"\n[ \t]*\n", "\n", text)
```

Gap: Triple newlines `\n\n\n` become `\n\n` instead of `\n`.

---

### 4. Recommended Fixes

#### Fix 1: Repair `_strip_annotations` 

Replace lines 294-295 with:
```python
# Safe patterns using explicit alternation (no catastrophic backtracking)
text = re.sub(r'(?:\[注\]|\[按\]|\[校勘記\]|\[案\]|【注】|【按】|【校勘記】|【案】)[^[【]*', '', text)
text = re.sub(r'（按：[^）]*）', '', text)
```

#### Fix 2: Improve `_normalize_whitespace` edge case

Add handling for triple+ newlines:
```python
text = re.sub(r"\n[ \t]*\n", "\n", text)
text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse 3+ newlines to paragraph break
```

#### Fix 3: Keep `_split_sentences` as-is

The current fix `r"([。！？；][ \t]*)"` is safe and working. No changes needed.

#### Fix 4: Keep `_recover_punctuation` as-is

This pattern was never broken. No changes needed.

---

### 5. Steps Taken

| Step | Tool/Method | Finding |
|------|-------------|---------|
| 1. Read source code | `Read` tool | Understood current implementation |
| 2. Analyzed regex patterns | Manual + `re.DEBUG` | Identified structural issues |
| 3. Created test scripts | Multiple Python files | Reproduced/rejected catastrophic claims |
| 4. Compared git diff | `git diff` | Found attempted fixes |
| 5. Tested actual behavior | Runtime tests | Discovered broken annotation matching |
| 6. Developed working patterns | Iterative testing | Created safe, functional replacements |
| 7. Verified performance | Timing tests | Confirmed linear-time behavior |

---

### 6. Tools Used

- **Read tool**: Source code analysis
- **Bash tool**: Running Python tests, git commands
- **Glob tool**: Finding test files
- **Custom test scripts**: 8 test files created to isolate issues
- **Python `re` module**: Pattern testing and verification

---

### 7. Verification Evidence

#### Performance Tests (all pass)
```
Input Size    | Time     | Status
--------------|----------|--------
11.7KB        | 0.0027s  | OK
58.6KB        | 0.0043s  | OK  
117.2KB       | 0.0087s  | OK
234.4KB       | 0.0178s  | OK
```

#### Existing Test Suite
```
14 passed in 0.02s
```

#### Pattern Matching Verification
- Proposed safe bracket pattern: **WORKS** on all test cases
- Proposed safe paren pattern: **WORKS** on all test cases  
- Performance: 50KB input processed in 0.0003s (linear time confirmed)

---

### Appendix: Test Files Created

1. `test_backtracking.py` - Initial reproduction attempt
2. `test_original_issues.py` - Testing original problematic patterns
3. `test_worst_case.py` - Worst-case input generation
4. `test_deep_analysis.py` - Deep regex structure analysis
5. `test_fix_verification.py` - Verifying attempted fixes
6. `test_actual_code.py` - Testing actual current code behavior
7. `test_debug_patterns.py` - Debugging pattern matching failures
8. `test_find_patterns.py` - Finding working pattern variations
9. `test_correct_patterns.py` - Correct pattern escaping
10. `test_final_verification.py` - Comprehensive final verification
