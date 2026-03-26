# Scenario 7: Quality Filter Code Review
## Condition: nopua | Run: 1
## Duration: 248.36s

---

## Quality Filter Code Review - Complete Assessment

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Unused numpy import** | Low | Line 20 |
| 2 | **Missing return type annotations** | Low | `train()`, `train_perplexity_model()`, `reset()` |
| 3 | **Private attribute access across classes** | Medium | Line 197: `self._scorer._trained` |
| 4 | **Dedup uses raw text instead of hash** | Medium | Line 263 |
| 5 | **Banned patterns only check output, not instruction** | High | `_check_content()` |
| 6 | **Perplexity check skipped unless model trained** | Medium | Line 197 |
| 7 | **Language check requires 30% Chinese (undocumented)** | High | Default config |
| 8 | **No text normalization for dedup** | Medium | `_check_dedup()` |
| 9 | **Sharp cutoff in repetition ratio at 10 chars** | Low | `_repetition_ratio()` |
| 10 | **Stats tracking is order-dependent** | Low | `_passes_all_checks()` |
| 11 | **No thread safety** | Medium | `_seen_hashes` set |
| 12 | **reset() doesn't reset perplexity model** | Low | `reset()` |
| 13 | **Unused type imports (Optional, Tuple)** | Low | Line 16 |
| 14 | **Inefficient n-gram list comprehension** | Low | Line 278 |

---

### 2. Hidden Issues Beyond the Ask

| # | Issue | Impact |
|---|-------|--------|
| H1 | **English-only data cannot be processed** - Default `min_chinese_ratio=0.3` filters out all English samples | Critical for multilingual use |
| H2 | **State leakage between filter instances** - Test shows qf_b affected by qf_a processing | Data corruption risk |
| H3 | **No regex caching** - Patterns recompiled per instance | Performance degradation |
| H4 | **Docstring example misleading** - Doesn't mention perplexity model needs training | User confusion |
| H5 | **Stats dict keys undocumented** | API usability issue |
| H6 | **No batch processing optimization** | Performance bottleneck for large datasets |
| H7 | **Misleading variable name `text_hash`** | Code maintainability |
| H8 | **Perplexity model edge case with single char** - Returns inflated scores | Quality degradation |

---

### 3. Root Causes

1. **Design assumptions not documented**: The filter assumes Chinese training data but this is not stated in docstrings or config comments.

2. **Encapsulation violations**: `QualityFilter` accesses `PerplexityScorer._trained` directly instead of using a property/method.

3. **Incomplete feature implementation**: Dedup was implemented as simple string comparison without proper hashing or normalization.

4. **Defensive coding gaps**: No validation for empty training data, no handling for edge cases in language detection.

5. **Performance not considered**: Regex compilation, n-gram generation, and sequential processing all lack optimization.

---

### 4. Recommended Fixes

#### Critical (Must Fix)
```python
# Fix 1: Remove unused import
# DELETE: import numpy as np

# Fix 2: Add proper encapsulation for PerplexityScorer
class PerplexityScorer:
    def is_trained(self) -> bool:  # NEW METHOD
        return self._trained

# In QualityFilter:
if not self._scorer.is_trained() or self._check_perplexity(sample):

# Fix 3: Document Chinese ratio requirement OR make it configurable per-sample
@dataclass
class FilterConfig:
    min_chinese_ratio: float = 0.3  # ADD COMMENT: Set to 0 for English-only data
```

#### High Priority
```python
# Fix 4: Check banned patterns in both fields
def _check_content(self, sample: Dict) -> bool:
    instruction = sample.get("instruction", "")
    output = sample.get("output", "")
    text = instruction + " " + output  # CHECK BOTH
    ...

# Fix 5: Use actual hash for dedup
import hashlib

def _check_dedup(self, sample: Dict) -> bool:
    dedup_text = sample.get(self.config.dedup_field, "")
    text_hash = hashlib.md5(dedup_text.strip().encode()).hexdigest()
    ...

# Fix 6: Add text normalization for dedup
def _check_dedup(self, sample: Dict) -> bool:
    dedup_text = sample.get(self.config.dedup_field, "")
    normalized = dedup_text.strip().lower()  # NORMALIZE
    text_hash = hashlib.md5(normalized.encode()).hexdigest()
```

#### Medium Priority
```python
# Fix 7: Add return type annotations
def train(self, reference_texts: List[str]) -> None:
def train_perplexity_model(self, reference_texts: List[str]) -> None:
def reset(self) -> None:

# Fix 8: Cache compiled patterns at class level
class QualityFilter:
    _cached_patterns: Dict[str, List[re.Pattern]] = {}  # CLASS CACHE
    
    def __init__(self, config: FilterConfig = None):
        pattern_key = tuple(config.banned_patterns)
        if pattern_key not in self._cached_patterns:
            self._cached_patterns[pattern_key] = [
                re.compile(p) for p in config.banned_patterns
            ]
        self._compiled_patterns = self._cached_patterns[pattern_key]
```

---

### 5. Steps Taken

1. **Read source file** - Analyzed `quality_filter.py` line by line
2. **Ran verification script** - Executed `verify_issues.py` to confirm suspected bugs
3. **Ran existing tests** - Executed `test_quality_filter.py` (13 passed, 1 failed)
4. **Ran comprehensive review** - Executed `comprehensive_review.py` for additional issues
5. **Interactive debugging** - Used Python REPL to trace through specific code paths
6. **Static analysis** - Used AST parsing to identify unused imports and missing type hints
7. **Pipeline integration check** - Reviewed `run_pipeline.py` to understand usage context

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code inspection |
| `Glob` | Find related test files |
| `Grep` | Search for module usage |
| `Bash` (Python REPL) | Interactive debugging |
| `Bash` (pytest) | Run test suite |
| `Bash` (verify_issues.py) | Confirm suspected bugs |
| `Bash` (comprehensive_review.py) | Extended code review |
| `ast` module | Static analysis |

---

### 7. Verification Evidence

**Test Results:**
```
tests/test_quality_filter.py: 13 PASSED, 1 FAILED
  - FAILED: test_near_duplicate_not_caught (test expectation bug, not code bug)
```

**Verified Bugs:**
- Unused numpy import confirmed via AST analysis
- Missing type hints confirmed via `inspect.signature()`
- Private attribute access confirmed at line 197
- Banned patterns in instruction NOT detected (tested interactively)
- Language check filters English-only data (ratio=0.0 < 0.3)
- Dedup uses raw text, not hash (line 263)

**Test Failure Analysis:**
The failing test `test_near_duplicate_not_caught` expected both samples to pass, but the test itself had samples that failed the length check (`min_output_length=20`). This is a **test bug**, not a code bug.
