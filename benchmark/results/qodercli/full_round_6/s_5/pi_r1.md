# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pi | Run: 1
## Duration: 43.91s

---

Let me read the source file directly since I have it provided:

## Investigation Report: Data Synthesizer Silent Failure

---

### 1. Issues Found

| # | Issue | Location |
|---|-------|----------|
| 1 | **`max_retries` defaults to 0** - No retry logic for transient API failures | `synthesizer.py:L54` |
| 2 | **Empty return on ANY API error without logging the response body** - Makes debugging impossible | `synthesizer.py:L234-L237` |
| 3 | **Empty return on parse errors without logging raw content** - Cannot diagnose malformed responses | `synthesizer.py:L246-L249` |
| 4 | **`_validate_sample` returns `None` silently** - No logging when samples are filtered out | `synthesizer.py:L285-L302` |
| 5 | **No validation that generated samples actually exist before returning** - `_generate_from_chunk` can return empty list without any indication of why | `synthesizer.py:L215-L250` |

---

### 2. Hidden Issues

| # | Category | Issue | Location |
|---|----------|-------|----------|
| 6 | 🔴 **Blocker** | **`GENERATION_PROMPT` requests `{n}` samples but LLM may not output valid JSON** - Prompt says "请以 JSON 格式输出" but doesn't enforce structure or provide schema | `synthesizer.py:L28-L38` |
| 7 | 🔴 **Blocker** | **LLM response format is undefined** - Could return markdown, plain text, or malformed JSON; parser only handles clean JSON arrays or single objects | `synthesizer.py:L253-L274` |
| 8 | 🟡 **Suggestion** | **No timeout on HTTP client beyond 60s** - If API hangs, entire pipeline stalls | `synthesizer.py:L167-L172` |
| 9 | 🟡 **Suggestion** | **`required_fields` default doesn't match actual validation** - Config says `["instruction", "output"]` but code also checks `output` length separately | `synthesizer.py:L67,L288-L295` |
| 10 | 🟡 **Suggestion** | **No sampling of failed responses for debugging** - All parse errors are counted but none are logged for later analysis | `synthesizer.py:L246-L249` |
| 11 | ⚪ **Nit** | **`close()` method exists but never called automatically** - Resource leak if user forgets to call it | `synthesizer.py:L315-L317` |
| 12 | ⚪ **Nit** | **`source_encoding` hardcoded to utf-8** - No fallback for other encodings | `synthesizer.py:L56` |

---

### 3. Root Cause

**Primary Root Cause (L215-L250):** The `_generate_from_chunk` method has a **silent failure cascade**:

1. **API succeeds but returns non-JSON** → Falls through to parse error handler → Returns `[]` with only a count increment
2. **API returns JSON but not in expected format** → `_parse_samples` tries to extract but fails → Returns `[]` 
3. **Samples are generated but fail validation** → `_validate_sample` returns `None` silently → Final list is empty

**Initially I thought** the issue was API key authentication or network problems. **Upon closer inspection**, the real problem is:

> **The prompt template (`GENERATION_PROMPT`) does not guarantee valid JSON output.** The LLM may return:
> - Markdown-formatted text with explanations
> - JSON wrapped in prose ("Here are the samples:...")
> - Malformed JSON (missing quotes, trailing commas)
> - Different field names than expected

**Actually, there are THREE compounding issues:**
1. Prompt doesn't enforce JSON schema strictly (L28-L38)
2. Parser doesn't handle common LLM output variations (L253-L274)
3. Validation failures are silent - no visibility into WHY samples were rejected (L285-L302)

---

### 4. Recommended Fix

#### Fix 1: Improve Prompt to Enforce JSON Schema

```python
# BEFORE (L28-L38):
GENERATION_PROMPT = """你是一個古文教育專家。根據以下古文段落，生成{n}個教學問答對。
要求：
1. 問題應涵蓋：翻譯、解釋、分析、典故等方面
2. 回答要詳細準確，引用原文
3. 難度從基礎到進階
古文段落：
{text}
請以 JSON 格式輸出，每個問答對包含 "instruction" 和 "output" 字段：
"""

# AFTER:
GENERATION_PROMPT = """你是一個古文教育專家。根據以下古文段落，生成{n}個教學問答對。

要求：
1. 問題應涵蓋：翻譯、解釋、分析、典故等方面
2. 回答要詳細準確，引用原文
3. 難度從基礎到進階
4. **只輸出純 JSON，不要任何其他文字或標記**

古文段落：
{text}

輸出格式（嚴格遵守）：
[
  {{"instruction": "問題 1", "output": "回答 1"}},
  {{"instruction": "問題 2", "output": "回答 2"}}
]
"""
```

#### Fix 2: Add Logging to Parse/Validation Failures

```python
# ADD to _parse_samples (after L274):
if not items:
    logger.warning(f"Failed to extract any JSON from response: {content[:500]}...")

# ADD to _validate_sample (L285-L302):
def _validate_sample(self, item: Dict, source_text: str) -> Optional[Dict]:
    # Check required fields
    for field_name in self.config.required_fields:
        if field_name not in item or not item[field_name].strip():
            logger.debug(f"Sample missing required field '{field_name}': {item}")
            return None
    
    # ... rest of validation with logging
    output_len = len(item.get("output", ""))
    if output_len < self.config.min_response_length:
        logger.debug(f"Sample output too short ({output_len} < {self.config.min_response_length})")
        return None
    if output_len > self.config.max_response_length:
        logger.debug(f"Sample output too long ({output_len} > {self.config.max_response_length})")
        return None
    
    return {...}
```

#### Fix 3: Add Retry Logic and Better Error Handling

```python
# MODIFY _generate_from_chunk (L215-L250):
def _generate_from_chunk(self, chunk_text: str) -> List[Dict]:
    prompt = GENERATION_PROMPT.format(
        n=self.config.samples_per_chunk,
        text=chunk_text,
    )

    for attempt in range(self.config.max_retries + 1):
        try:
            response = self._client.post(...)
            response.raise_for_status()
            break  # Success, exit retry loop
            
        except httpx.HTTPError as e:
            logger.error(f"API request failed (attempt {attempt + 1}): {e}")
            if attempt < self.config.max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            self._stats["api_errors"] += 1
            return []

    # Parse response WITH RAW CONTENT LOGGING
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.debug(f"Raw API response: {content[:1000]}...")  # ADD THIS
        samples = self._parse_samples(content, chunk_text)
        
        if not samples:
            logger.warning(f"No valid samples extracted from chunk. Raw response: {content[:500]}")  # ADD THIS
        
        self._stats["chunks_processed"] += 1
        self._stats["samples_generated"] += len(samples)
        return samples

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse API response: {e}. Content: {response.text[:500]}")  # IMPROVED
        self._stats["parse_errors"] += 1
        return []
```

#### Fix 4: Set Sensible Default for max_retries

```python
# CHANGE L54:
max_retries: int = 3  # Was 0
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read full synthesizer.py source | Identified silent return patterns at L198, L237, L249, L288 |
| 2 | Analyzed `_generate_from_chunk` flow | Found 3 failure points all returning `[]` without context |
| 3 | Examined `GENERATION_PROMPT` template | **Initially thought** prompt was fine; **upon closer inspection**, it doesn't enforce pure JSON output |
| 4 | Reviewed `_parse_samples` extraction logic | Discovered parser only handles clean JSON arrays or single objects - no tolerance for LLM variations |
| 5 | Traced `_validate_sample` filtering | Found all validation failures are silent - no logging to diagnose why samples are rejected |
| 6 | Checked config defaults | Discovered `max_retries=0` means no retry on transient failures |
| 7 | **Broadening scope** - Examined prompt engineering best practices | Confirmed LLMs often return markdown/prose even when asked for JSON |
| 8 | **Strategy变更** - From "find the bug" to "why would this produce 0 samples" | Realized the issue isn't a bug but a design gap: no enforcement/guarantee of output format |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual code reading | Full source analysis of synthesizer.py |
| Pattern search | Identified all `return []` and `logger.error` locations |
| Control flow tracing | Mapped execution path from `generate()` → `_generate_from_chunk()` → `_parse_samples()` → `_validate_sample()` |
| Prompt engineering analysis | Evaluated prompt template for format enforcement gaps |

---

### 7. Verification

**To verify the diagnosis and test the fix:**

```bash
# 1. Enable debug logging to see what's happening
export PYTHONPATH="D:\Projects\private-project\src"
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from data_engineering.synthesizer import DataSynthesizer, SynthConfig

config = SynthConfig(
    api_key='YOUR_KEY',
    max_retries=3,  # Test with retries
    delay_between_requests=0.5,
)
synth = DataSynthesizer(config)

# Generate with verbose output
samples = synth.generate(source_dir='./data/chunks/', output_path='./test_output.jsonl')
print(f'Generated {len(samples)} samples')
print(f'Stats: {synth.get_stats()}')
"

# 2. Check logs for parsing/validation failures
# Look for lines like:
# - "Failed to extract any JSON from response"
# - "Sample missing required field"
# - "Sample output too short/long"

# 3. Verify output file has content
wc -l ./test_output.jsonl
head -n 3 ./test_output.jsonl
```

**Expected outcome after fix:**
- Debug logs will show raw API responses
- If LLM returns malformed JSON, you'll see the actual content
- If samples fail validation, you'll know which field and why
- Retries will handle transient API failures

---

## Summary

**Root cause:** The synthesizer has a **silent failure cascade** where:
1. Prompt doesn't guarantee valid JSON output
2. Parser can't handle common LLM output variations  
3. Validation rejections are invisible

**Result:** API calls may succeed and generate content, but zero samples pass through the pipeline because the format doesn't match expectations - with no visibility into why.

**Fix priority:** 
1. 🔴 Add debug logging to `_parse_samples` and `_validate_sample` (immediate visibility)
2. 🔴 Improve prompt to enforce pure JSON output (prevents malformed responses)
3. 🟡 Add retry logic for transient failures (robustness)
