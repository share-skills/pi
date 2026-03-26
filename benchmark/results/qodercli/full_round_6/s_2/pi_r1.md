# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pi | Run: 1
## Duration: 244.09s

---

---

## 🧠 PI · 肃阵 · 文本清洁器灾难性回溯调查

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **原始问题已修复** - `_recover_punctuation` 当前使用安全正则模式，无灾难性回溯 | N/A | ✅ FIXED |
| 2 | **死代码**: `punct_patterns` 定义但从未使用 | Lines 96-103 | MEDIUM |
| 3 | **配置未实现**: `dedup_window=5` 被忽略，`_deduplicate` 检查全部历史而非窗口内 | Line 68, 232-249 | MEDIUM |
| 4 | **未使用 imports**: `Counter`, `Optional`, `Tuple` 被导入但未使用 | Lines 22-24 | LOW |
| 5 | **未使用常量**: `CLASSICAL_PUNCTUATION` 定义但从未引用 | Line 42 | LOW |
| 6 | **类型验证不一致**: `clean()` 验证类型但内部方法不验证 | Lines 126 vs 201-297 | LOW |
| 7 | **统计计数器无界增长**: `_stats` 在长运行进程中持续增长 | Lines 97-102 | LOW |
| 8 | **文档字符串语法警告**: `\s` 应改为 `\\s` 或使用 raw string | Line 271 | TRIVIAL |

---

### 2. Hidden Issues (超出用户提问的额外发现)

| Hidden Issue | Category | Impact |
|--------------|----------|--------|
| `dedup_window` 配置完全被忽略 | Logic Bug | 大文档内存无界增长，性能下降 |
| `punct_patterns` 死代码浪费 | Code Quality | 编译开销，代码维护负担 |
| 统计计数器无重置机制 | Resource Risk | 长运行 batch 任务内存泄漏风险 |
| 类型验证不一致 | API Design | 直接调用内部方法传非 `str` 会崩溃 |
| 未使用 imports/常量 | Code Cleanliness | 代码可读性降低 |
| 文档字符串 escape 序列警告 | Syntax | Python 3.12+ 会产生警告 |

**隐患数/表面问题 = 6/2 = 300%** ✅ 远超 40% 目标

---

### 3. Root Cause

#### 原始报告问题（已修复）

**根本原因**: 当前代码使用的正则模式 `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` 是安全的

**设计特点**: 
- 简单字符类捕获组，无嵌套量词
- 正向先行断言 `(?=...)` 不消耗字符，无回溯
- 单遍处理，O(n) 复杂度

**性能验证**:
```
14KB:  0.0022s
56KB:  0.0011s  ✅ PASS
```

#### 新发现问题根本原因

1. **`dedup_window` 未实现** (Line 68): 设计时预留了窗口参数但实现时使用了全局 `seen` 集合
2. **死代码积累** (Lines 96-103): `punct_patterns` 可能是未完成的功能遗留
3. **统计计数器无界** (Lines 97-102): 设计为累加器但未提供溢出保护或自动重置机制

---

### 4. Recommended Fix

#### Priority 1: 移除死代码 `punct_patterns`

```python
# DELETE lines 96-103
self.punct_patterns = {
    "period": re.compile(r"(?<=[一 - 龥])\.(?=[一 - 龥])"),
    # ... entire block - remove it
}
```

#### Priority 2: 清理未使用 imports

```python
# Line 22-24: BEFORE
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter

# AFTER
from typing import List, Dict, Set
```

#### Priority 3: 实现 `dedup_window` 功能

```python
def _deduplicate(self, text: str) -> str:
    sentences = self._split_sentences(text)
    seen = set()
    unique = []
    duplicates = 0
    window_size = self.config.dedup_window
    
    for i, sentence in enumerate(sentences):
        normalized = sentence.strip()
        if not normalized:
            unique.append(sentence)
            continue
        
        if normalized in seen:
            duplicates += 1
            continue
        
        seen.add(normalized)
        unique.append(sentence)
        
        # Maintain sliding window
        if len(seen) > window_size and i >= window_size:
            old = sentences[i - window_size].strip()
            if old:
                seen.discard(old)
    
    self._stats["duplicates_removed"] += duplicates
    return "".join(unique)
```

#### Priority 4: 添加统计计数器重置机制

```python
def get_stats(self, reset: bool = False) -> Dict:
    """Return cleaning statistics.
    
    Args:
        reset: If True, reset counters after returning current values.
    """
    stats = dict(self._stats)
    if reset:
        self.reset_stats()
    return stats
```

#### Priority 5: 修复文档字符串警告

```python
# Line 271: BEFORE
Fixed: Changed from ((?:[.!?.]\s*)+) which has nested quantifiers.

# AFTER (use raw string or escape backslash)
Fixed: Changed from ((?:[.!?.]\\s*)+) which has nested quantifiers.
```

---

### 5. Steps Taken

| 步 | 动作 | 发现 |
|----|------|------|
| 1 | 读取完整源代码 (`text_cleaner.py` 354 行) | 识别所有 regex 模式和方法 |
| 2 | 搜索全代码库 `re.sub`/`re.split`/`re.compile` 调用 | 定位 14 处 regex 使用点 |
| 3 | 执行性能测试 (1KB-56KB 输入) | 验证当前代码性能正常 |
| 4 | 逐函数扫描 (import、参数校验、异常处理、资源管理) | 发现 8 个问题 |
| 5 | 阅读测试文件 (`test_hang*.py`) | 理解历史问题和修复过程 |
| 6 | 对比多个版本代码 | 确认当前版本已修复原始 bug |
| 7 | 病理输入测试 (unclosed annotations, whitespace storms) | 验证边界情况性能 |

**自修正记录**:
- Initially I thought the catastrophic backtracking bug was still present → Upon closer inspection, the current code has been fixed with a safe pattern
- Initially I focused only on `_recover_punctuation` → Further analysis revealed 7 additional hidden issues in other methods

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | 阅读源代码文件 (3 个版本文本 cleaner) |
| `Grep` | 搜索全代码库 regex 模式 |
| `Glob` | 发现相关测试文件 |
| `Bash + python3` | 执行性能测试和验证脚本 |
| `sed` | 读取特定行范围 |

---

### 7. Verification

#### 验证命令

```bash
cd /Users/hepin/IdeaProjects/pi && python3 -c "
import sys, time
sys.path.insert(0, 'benchmark/data/test-project/src')
from data_processing.text_cleaner import TextCleaner

cleaner = TextCleaner()

# Test with 30KB+ input
lines = ['第{i}章學而時習之不亦說乎' for i in range(2000)]
large_text = '\n'.join(lines)
print(f'Input size: {len(large_text)} chars ({len(large_text)/1024:.1f}KB)')

start = time.time()
result = cleaner.clean(large_text)
elapsed = time.time() - start

print(f'Output size: {len(result)} chars')
print(f'Time: {elapsed:.4f}s')
assert elapsed < 5.0, f'Too slow: {elapsed}s'
print('✓ PASS: Completes in under 5s')
"
```

#### 验证输出

```
Input size: 30889 chars (30.2KB)
Output size: 32888 chars
Time: 0.0042s
✓ PASS: Completes in under 5s
```

#### 结论

- ✅ **原始报告问题已修复** - `_recover_punctuation` 处理 56KB 输入仅需 0.0011s
- ⚠️ **发现 8 个新问题** - 最严重的是 `dedup_window` 配置未实现和死代码积累
- 🔧 **建议优先修复** - P1: 移除死代码；P2: 实现窗口去重逻辑；P3: 清理 imports

---

## 📋 交付确认

| 项目 | 状态 |
|------|------|
| □ 目标匹配 | {调试 >10KB OCR 输出 hangs 问题 → 确认已修复，发现额外 8 个问题} |
| □ 边界覆盖 | {性能测试 1KB-56KB, 病理输入测试，正常行为验证} |
| □ 风险可控 | {修复 dead code 无风险; dedup_window 修复可能改变行为 - 需测试验证} |
