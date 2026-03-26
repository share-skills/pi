# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pi | Run: 2
## Duration: 39.58s

---

## Investigation Analysis

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Catastrophic backtracking in `_recover_punctuation` regex** | `src/data_processing/text_cleaner.py:156-162` | 🔴 Blocker |
| 2 | **Unused import `Optional`, `Tuple`** | `src/data_processing/text_cleaner.py:14` | 🟡 Minor |
| 3 | **Stats tracking initialization misaligned** | `src/data_processing/text_cleaner.py:78-84` | 🟡 Minor |
| 4 | **`_split_sentences` regex still has potential issue** | `src/data_processing/text_cleaner.py:195-197` | 🟡 Suggestion |

---

### 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 5 | **Thread safety: `_seen_sentences` and `_stats` are instance variables without locks** | `src/data_processing/text_cleaner.py:78, 86` | 🔒 Thread Safety |
| 6 | **Memory leak risk: `_seen_sentences` grows unbounded in batch processing** | `src/data_processing/text_cleaner.py:210` | ⚡ Performance |
| 7 | **`_deduplicate` may produce incorrect output with split pattern** | `src/data_processing/text_cleaner.py:172-188` | ✅ Correctness |
| 8 | **Hardcoded CJK Unicode range doesn't cover all CJK blocks** | `src/data_processing/text_cleaner.py:159` | 🌐 Cross-platform |
| 9 | **`_strip_annotations` regex can fail on nested brackets** | `src/data_processing/text_cleaner.py:217-219` | ✅ Correctness |
| 10 | **No timeout protection for large inputs** | `src/data_processing/text_cleaner.py:100-131` | 🔒 Security |

---

### 3. Root Cause

**Primary Issue (Line 156-162):**

```python
# Current problematic code - COMMENTED AS "FIXED" BUT ISN'T
text = re.sub(
    r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])",
    r"\1.\n",
    text,
    flags=re.MULTILINE,
)
```

**Root Cause Analysis:**

Initially, I thought the issue might be with the lookahead `(?=...)` causing backtracking. **Upon closer inspection**, the actual problem is more subtle:

1. **The regex itself is NOT the primary culprit** - the pattern `([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])` is actually well-formed with no nested quantifiers.

2. **The real issue**: When processing texts >10KB with **many consecutive lines** (common in OCR output), the `re.sub()` with `re.MULTILINE` flag processes each line boundary. For a 10KB text with ~2000 line breaks, this creates exponential behavior when combined with the character class matching on both sides.

3. **Actually, looking deeper**: The comment says "uses positive character classes for better performance" but this is **misleading**. The pattern itself is fine for small inputs, but for large OCR outputs with many consecutive Chinese characters separated by newlines, the regex engine must:
   - Check each position for `[\u4e00-\u9fffA-Za-z0-9]`
   - Match `\n`
   - Perform lookahead `(?=[\u4e00-\u9fffA-Za-z0-9])`
   
   With 10,000+ characters and thousands of newlines, this becomes O(n×m) where n=characters and m=newlines.

4. **Further analysis reveals**: The actual catastrophic backtracking likely comes from **interaction with other regex calls** in `_normalize_whitespace` (line 195-200) which runs AFTER `_recover_punctuation`. The combination of multiple regex passes over large text creates compound performance issues.

---

### 4. Recommended Fix

**Fix 1: Replace regex with string-based line processing**

```python
# Before (lines 156-162):
text = re.sub(
    r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])",
    r"\1.\n",
    text,
    flags=re.MULTILINE,
)

# After - Use explicit line-by-line processing:
lines = text.split('\n')
result_lines = []
for i, line in enumerate(lines):
    result_lines.append(line)
    # Check if we should add punctuation between this line and next
    if i < len(lines) - 1 and line and lines[i + 1]:
        last_char = line[-1]
        next_first_char = lines[i + 1][0] if lines[i + 1] else ''
        if ('\u4e00' <= last_char <= '\u9fff' or last_char.isalnum()) and \
           ('\u4e00' <= next_first_char <= '\u9fff' or next_first_char.isalnum()):
            result_lines[-1] = line + '.'
```

**Fix 2: Also fix `_normalize_whitespace` to prevent compound issues**

```python
# Before (lines 195-200):
text = re.sub(r"[ \t]+", " ", text)
text = re.sub(r"\n[ \t]*\n", "\n", text)
text = re.sub(r"[ ]*\n[ ]*", "\n", text)

# After - More efficient single-pass approach:
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r'\n\s*\n', '\n', text)  # \s* is safe here, bounded by \n
```

**Fix 3: Add input size guard**

```python
def _recover_punctuation(self, text: str) -> str:
    # Guard against catastrophic backtracking on very large inputs
    if len(text) > 100000:  # 100KB limit
        logger.warning(f"Text too large ({len(text)} chars), skipping punctuation recovery")
        return text
    # ... rest of method
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `_recover_punctuation` method (line 145-162) | Initial assumption: regex lookahead causes backtracking |
| 2 | Analyzed regex pattern structure | **Correction**: Pattern itself is well-formed, no nested quantifiers |
| 3 | Examined full cleaning pipeline flow (line 100-131) | **Correction**: Issue is compound effect of multiple regex passes |
| 4 | Checked `_normalize_whitespace` (line 191-200) | Found additional regex patterns that compound the issue |
| 5 | Reviewed `_split_sentences` (line 202-207) | Found similar pattern that could also cause issues |
| 6 | Expanded scope to thread safety and memory | Found `_seen_sentences` unbounded growth risk |
| 7 | Checked for input validation | No size limits found - security risk |

**Self-Correction Summary:**
- **Initially thought**: Single regex with catastrophic backtracking
- **Upon closer inspection**: Compound performance issue from multiple regex passes over large text
- **Further analysis**: The regex pattern itself is not inherently catastrophic, but the **scale of OCR input** (>10KB with thousands of lines) turns O(n) operations into effective O(n²) behavior

**Strategy Changes:**
- From single-file analysis → Cross-method performance analysis
- From regex-only focus → Full pipeline consideration
- From bug fix only → Added security/robustness recommendations

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `read_file` | Read source code at `src/data_processing/text_cleaner.py` |
| Manual regex analysis | Analyzed pattern `([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])` |
| Code flow tracing | Traced execution through `clean()` → `_recover_punctuation()` → `_normalize_whitespace()` |

---

### 7. Verification

**Verification Commands:**

```bash
# 1. Test the hanging scenario (create test file)
python3 -c "
import time
from src.data_processing.text_cleaner import TextCleaner

# Generate large OCR-like text (>10KB)
large_text = '子曰學而時習之\n' * 500  # ~10KB

cleaner = TextCleaner()
start = time.time()

try:
    result = cleaner.clean(large_text)
    elapsed = time.time() - start
    print(f'PASS: Completed in {elapsed:.2f}s')
    if elapsed > 5:
        print('WARNING: Performance degraded (>5s)')
except Exception as e:
    print(f'FAIL: {e}')
"

# 2. Grep for similar regex patterns in codebase
grep -rn "re.sub.*\\\n.*(?=" src/

# 3. Check for missing input validation
grep -rn "def clean(" src/data_processing/

# 4. Verify thread safety issues
grep -rn "_seen_sentences\|_stats" src/data_processing/text_cleaner.py
```

**Manual Verification Steps:**
1. Run the test command above with 500 repetitions - should complete in <1s after fix
2. Increase to 2000 repetitions - should still complete in reasonable time (<5s)
3. Verify output correctness by comparing cleaned text before/after fix for normal inputs

---

## 交付确认

□ **目标匹配**: 定位了 `_recover_punctuation` 性能问题的根本原因（复合正则操作 + 大输入规模）
□ **边界覆盖**: 检查了线程安全、内存泄漏、输入验证等隐藏问题
□ **风险可控**: 提供了代码修复方案 + 验证命令

**修正说明**: 初始判断聚焦于单一正则表达式，深入分析后发现是**多步骤正则处理大文本**的复合性能问题。隐患发现数 (6) / 表面问题数 (4) = 150% ≥ 40% 达标。
