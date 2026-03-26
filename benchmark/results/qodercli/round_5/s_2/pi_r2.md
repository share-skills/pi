# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pi | Run: 2
## Duration: 251.42s

---

## 调查结果总结

### 1. Issues Found

**核心发现：报告的 `_recover_punctuation`  hangs 问题是误诊**

| # | 问题 | 位置 | 状态 |
|---|------|------|------|
| 1 | **误诊的根本原因** | 任务描述 | `_recover_punctuation` 当前实现使用线性时间正则，无回溯风险 |
| 2 | **历史遗留注释** | `benchmark/data/text_cleaner.py:272-278` | 注释提到已修复的嵌套量词模式 `((?:[.!?;]\s*)+)` |
| 3 | **代码版本不一致** | 三个文件有不同实现 | `benchmark/src/` (最新) vs `benchmark/data/` vs `nopua/benchmark/` |

### 2. Hidden Issues

| # | 隐患类型 | 位置 | 描述 |
|---|----------|------|------|
| H1 | **统计计算错误** | `benchmark/data/text_cleaner.py:169` | `lines_removed` 使用 `original_len - len(lines)`（字符数减行数），单位不匹配 |
| H2 | **类型检查缺失** | `nopua/text_cleaner.py:132-133` | 缺少 `isinstance(text, str)` 检查 |
| H3 | **未使用的 import** | `text_cleaner.py:22` | `Tuple`, `Optional` 导入但未使用 |
| H4 | **配置验证缺失** | `CleanerConfig:66` | `min_line_length=2` 无范围校验 |
| H5 | **线程安全问题** | `TextCleaner:93` | `_seen_sentences` 在 batch 操作中可能被并发修改 |
| H6 | **依赖缺失处理** | `text_cleaner.py:107-109` | `opencc` 导入失败仅记录警告，后续调用会崩溃 |

### 3. Root Cause

**误诊分析**：
- **初始判断**：用户报告 `_recover_punctuation` 在处理 >10KB OCR 文本时 hangs
- **深入验证后**：该方法的正则模式 `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` 是**线性时间 O(n)**：
  - 使用正向前瞻 `(?=...)`，不消耗字符，无回溯可能
  - 字符类 `[\u4e00-\u9fffA-Za-z0-9]` 是原子匹配，无嵌套量词
  - 实测 10KB+ 文本在 0.004s 内完成

**真正可能导致 hangs 的历史模式**（已在注释中标记为已修复）：
- `_split_sentences` 原模式 `((?:[.!?;]\s*)+)` — 嵌套量词 `(X+)+` 是经典 ReDoS 模式
- 输入如 `". . . ... x"` 可触发指数级回溯 O(2^n)

### 4. Recommended Fix

```python
# 1. 修复 stats 计算错误 (benchmark/data/text_cleaner.py:166-168)
# 修改前:
removed = original_len - len(lines)  # 字符数 - 行数 = 无意义

# 修改后:
lines_removed_count = original_line_count - len(lines)
if lines_removed_count > 0:
    self._stats["lines_removed"] += lines_removed_count

# 2. 添加类型检查 (nopua 版本缺失)
def clean(self, text: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    # ...

# 3. 清理未使用 imports
# 删除: from typing import List, Dict, Set, Optional, Tuple
# 改为: from typing import List, Dict, Set
```

### 5. Steps Taken

1. **读取三个版本的 text_cleaner.py** — 确认 `benchmark/src/` 是最新修复版本
2. **分析 `_recover_punctuation` 正则** — 验证模式为线性时间，无回溯风险
3. **测试所有正则模式性能** — 创建 `test_text_cleaner_performance.py`，实测全部通过
4. **搜索历史注释** — 发现 `((?:[.!?;]\s*)+)` 已被修复的嵌套量词模式
5. **逐行审查代码** — 发现 stats 计算错误、类型检查缺失等 6 个隐藏问题
6. **验证经典 ReDoS 模式** — 用 `^((?:a+)+)b` + `a^35` 确认 5 秒超时，对比当前模式安全

**假设修正**：
- Initially I thought: `_recover_punctuation` 的正则模式存在 catastrophic backtracking
- Upon closer inspection: 该模式使用正向前瞻 + 原子字符类，**不可能**发生灾难性回溯
- 实际上：用户报告的 hangs 可能是由其他原因导致（如 Dedup  pipeline、I/O 阻塞、或旧版本代码）

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `Read` | 读取三个版本文本 cleaner 源码 |
| `Grep` | 搜索 `re.sub`/`re.split` 所有正则模式 |
| `Bash` | 运行 Python 测试脚本验证正则性能 |
| `Glob` | 定位所有 `text_cleaner.py` 文件 |

### 7. Verification

**验证命令**：
```bash
# 运行完整性能测试套件
cd /Users/hepin/IdeaProjects/pi
python3 test_text_cleaner_performance.py

# 预期输出:
# - 所有正则模式在 <0.01s 内完成
# - 无 TIMEOUT 警告
# - 10KB+ 文本处理正常
```

**人工检查步骤**：
1. 检查 `benchmark/data/text_cleaner.py:169` — 确认 `lines_removed` 计算是否使用 `original_line_count`
2. 检查 `nopua/text_cleaner.py:132` — 确认是否有 `isinstance(text, str)` 检查
3. 检查所有 `import` 语句 — 确认 `Optional`, `Tuple` 是否被使用

---

## 交付确认

□ **目标匹配**: 调查了 `_recover_punctuation` hangs 问题 → 证实为误诊，当前实现安全  
□ **边界覆盖**: 测试了 >10KB 中文/英文/混合文本，验证所有正则模式性能  
□ **风险可控**: 发现 6 个隐藏问题（stats 错误、类型检查缺失等），附修复建议
