# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pi | Run: 2
## Duration: 142.39s

---

Now I have a complete picture. Let me compile the full investigation report:

---

## 🧠 PI · 調查報告 · Data Synthesizer Silent Failure

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Logging not configured** - errors logged to nowhere | synthesizer.py:35, 230, 244 | 🔴 blocker |
| 2 | **Prompt lacks explicit JSON schema** - LLM may return wrong format | synthesizer.py:40-51 | 🔴 blocker |
| 3 | **No "JSON only" instruction** - LLM adds explanatory text breaking JSON parse | synthesizer.py:40-51 | 🔴 blocker |
| 4 | **Empty API key silently fails** - 401 error logged but user sees nothing | synthesizer.py:66, 112-118 | 🔴 blocker |
| 5 | **No validation of generated samples** - empty output file created without warning | synthesizer.py:165, 306-315 | 🟡 major |
| 6 | **_parse_samples loses items on partial JSON failure** - no fallback for malformed responses | synthesizer.py:248-283 | 🟡 major |
| 7 | **Unused import** - `re` imported inside method, not at module level | synthesizer.py:264 | ⚪ minor |

---

### 2. Hidden Issues

| # | Issue | Location | Risk |
|---|-------|----------|------|
| H1 | **No retry mechanism** - config has `max_retries: 0`, transient API failures cause permanent sample loss | synthesizer.py:78, configs/synth_config.yaml:17 | Reliability |
| H2 | **Validation silently drops short outputs** - `min_response_length: 50` may filter out valid short Q&A pairs | synthesizer.py:294-295, config:24 | Data quality bias |
| H3 | **Hardcoded API base URL** - no support for alternative LLM providers without code changes | synthesizer.py:65 | Flexibility |
| H4 | **No timeout configuration for rate limiting** - fixed `delay_between_requests` regardless of API response | synthesizer.py:77 | Efficiency |
| H5 | **Resource leak risk** - `_client.close()` only called via explicit `close()`, no context manager or `__del__` | synthesizer.py:112-119, 321-323 | Connection exhaustion |
| H6 | **Stats not exposed during generation** - user can't monitor progress in real-time | synthesizer.py:120-125 | UX |
| H7 | **No chunk size validation** - very long chunks may exceed `max_tokens` limit | synthesizer.py:199-207 | Runtime failure |

---

### 3. Root Cause

**Primary Root Cause (多重根因):**

1. **Logging Configuration Missing** (synthesizer.py:35):
   ```python
   logger = logging.getLogger(__name__)
   # No logging.basicConfig() anywhere → errors logged to void
   ```
   Initially I thought this was just an API issue. Upon closer inspection, **the logging setup is completely absent**, meaning all `logger.error()` calls (lines 230, 244) produce zero visible output.

2. **Prompt Engineering Deficiency** (synthesizer.py:40-51):
   - Prompt says "請以 JSON 格式輸出" but provides **no example output structure**
   - No instruction to return **only** JSON (LLMs typically add explanatory text)
   - Field names in English (`instruction`, `output`) but prompt in Chinese → potential schema mismatch

3. **Silent Failure on Empty Results** (synthesizer.py:165, 306-315):
   ```python
   self._save_results(all_samples, output_path)  # all_samples = []
   # Creates empty file, logs "Saved 0 samples" at INFO level (not visible)
   ```
   Actually, the code proceeds to save an empty file without any warning or error.

**实际上，问题比初始判断更复杂：** 不仅是"API 调用失败"，而是**三层防御全部失效**:
- Layer 1: Logging invisible → user doesn't see errors
- Layer 2: Prompt weak → LLM returns unparsable content  
- Layer 3: No validation → empty output treated as success

---

### 4. Recommended Fix

#### Fix 1: Configure Logging (synthesizer.py)
```python
# Add after imports (before line 35)
def _setup_logging():
    """Configure logging if not already configured."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

_setup_logging()
```

#### Fix 2: Improve Prompt Template (synthesizer.py:40-51)
```python
GENERATION_PROMPT = """你是一個古文教育專家。根據以下古文段落，生成{n}個教學問答對。

要求：
1. 問題應涵蓋：翻譯、解釋、分析、典故等方面
2. 回答要詳細準確，引用原文
3. 難度從基礎到進階
4. **只輸出 JSON，不要任何解釋文字**

古文段落：
{text}

輸出格式（必須嚴格遵守）：
[
  {{"instruction": "問題 1", "output": "答案 1"}},
  {{"instruction": "問題 2", "output": "答案 2"}}
]

範例：
輸入：子曰：學而時習之，不亦說乎？
輸出：[{{"instruction": "翻譯這段話", "output": "孔子說：學習並且時常複習，這不是很愉快嗎？"}}]

請開始輸出 JSON："""
```

#### Fix 3: Validate Output Before Saving (synthesizer.py:165)
```python
# Before saving, validate that samples were generated
if not all_samples:
    logger.error("CRITICAL: No samples generated! Check API key and logs above.")
    raise RuntimeError("Sample generation failed - output would be empty")

self._save_results(all_samples, output_path)
```

#### Fix 4: Handle API Key Validation Early (synthesizer.py:111)
```python
def __init__(self, config: SynthConfig = None):
    # ... existing config loading ...
    
    if not self.config.api_key:
        raise ValueError(
            "API key is empty. Set OPENAI_API_KEY environment variable "
            "or provide api_key in config."
        )
    
    self._client = httpx.Client(...)
```

#### Fix 5: Use Context Manager for HTTP Client (synthesizer.py)
```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()
    return False

# Usage:
# with DataSynthesizer(config) as synth:
#     synth.generate(...)
```

---

### 5. Steps Taken

| Step | Action | Discovery |
|------|--------|-----------|
| 1 | Read synthesizer.py source code | Found logging configured but no `basicConfig()` call |
| 2 | Read config file (synth_config.yaml) | Confirmed `api_key: ""` relies on env var |
| 3 | Tested JSON parsing logic with various LLM response formats | Discovered silent failures when LLM adds intro text |
| 4 | Simulated `_parse_samples()` flow with edge cases | Found 4 scenarios all returning 0 samples |
| 5 | Checked logging configuration at runtime | Confirmed root logger has 0 handlers → silent |
| 6 | Analyzed GENERATION_PROMPT template | Identified missing schema example and "JSON only" instruction |
| 7 | Traced complete execution flow from `generate()` to `_save_results()` | Found empty list flows through without error |
| 8 | Searched for retry/validation logic | Confirmed no retry, no output validation |

**自修正记录:**
- Initially I thought the issue was just "API key not set". Upon closer inspection, even with a valid API key, the **prompt engineering issues** and **missing logging** would still cause silent failures.
- Initially I assumed `_parse_samples()` handles malformed JSON gracefully. Actually, it **silently drops** any response that isn't clean JSON or markdown-wrapped JSON.

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read synthesizer.py, synth_config.yaml, test data files |
| `Glob` | Locate synthesizer.py copies and config files |
| `Grep` | Search for logging calls, parsing logic, prompt usage |
| `Bash` (python3 -c) | Test JSON parsing edge cases, simulate flow, verify logging behavior |

---

### 7. Verification

**验证命令:**

```bash
# 1. Verify logging fix works
cd /path/to/project/src/data_engineering
python3 -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('test')
logger.error('This should now be visible')
"

# 2. Test prompt improvement (simulate LLM response)
python3 -c "
import json
import re

# Improved prompt should produce this format:
test_output = '''[{\"instruction\": \"翻譯\", \"output\": \"孔子說：學習並且時常複習...\"}]'''
try:
    parsed = json.loads(test_output)
    print(f'Valid JSON array with {len(parsed)} items')
except:
    print('Parse failed')
"

# 3. Run synthesizer with verbose logging to see actual errors
OPENAI_API_KEY="" python3 -c "
from synthesizer import DataSynthesizer, SynthConfig
import logging
logging.basicConfig(level=logging.DEBUG)

config = SynthConfig(api_key='')  # Empty key to trigger error
try:
    synth = DataSynthesizer(config)
except ValueError as e:
    print(f'Caught early validation: {e}')
"

# 4. Check output file after failed run
ls -la ./data/synthetic_training.jsonl
wc -l ./data/synthetic_training.jsonl  # Should show 0 lines if bug present
```

**验证证据:**

```
Before fix:
- Script exits with code 0
- Output file exists but 0 bytes
- No error messages visible

After fix (expected):
- Script raises ValueError or RuntimeError on empty samples
- Error messages visible: "API request failed", "No samples generated"
- User immediately knows to check API key / prompt
```

---

### 📋 交付确认

| 检查项 | 状态 |
|--------|------|
| ✅ 目标匹配 | Silent failure root causes identified (logging + prompt + validation) |
| ✅ 边界覆盖 | 7 surface issues + 7 hidden issues documented with line numbers |
| ✅ 风险可控 | 提供 5 个具体修复方案，附代码示例 |
| ✅ 验证路径 | 给出 4 条验证命令，可执行 |

**明约:**
```
📋 交付确认
□ 目标匹配：静默失败根因已定位（日志配置缺失 + 提示词工程缺陷 + 空输出无验证）
□ 边界覆盖：表面问题 7 项 + 隐藏隐患 7 项，均附 file:line 证据
□ 风险可控：5 个修复方案含代码示例，按优先级排序
```
