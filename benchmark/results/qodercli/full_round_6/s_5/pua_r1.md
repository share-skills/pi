# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pua | Run: 1
## Duration: 70.69s

---

Now let me trace through the complete data flow to identify all failure points:

## Investigation Complete — Multiple Critical Issues Found

### 1. ROOT CAUSE ANALYSIS

After tracing through the entire code path from input → API → parsing → validation → output, I've identified **5 distinct issues** that could cause silent failure:

---

### 2. ISSUES FOUND

#### **Issue #1: CRITICAL — Validation silently drops samples without "instruction" field (Line 288-290)**

**Location:** `synthesizer.py:288-290`

```python
for field_name in self.config.required_fields:
    if field_name not in item or not item[field_name].strip():
        return None  # Silent rejection - no logging!
```

**Problem:** The LLM response parser expects `instruction` and `output` fields, but the GENERATION_PROMPT only asks for these fields WITHOUT explicitly guaranteeing they'll be present. If the LLM returns a different structure (e.g., `question`/`answer`, `q`/`a`, or narrative text), samples are silently rejected.

**Evidence:** Look at line 40-51 of the prompt - it says "請以 JSON 格式輸出，每個問答對包含 "instruction" 和 "output" 字段" but LLMs often don't follow this exactly, especially with markdown formatting.

---

#### **Issue #2: CRITICAL — JSON extraction regex misses unmarked JSON (Line 265)**

**Location:** `synthesizer.py:265`

```python
json_blocks = re.findall(r"```json?\s*(.*?)```", content, re.DOTALL)
```

**Problem:** This regex ONLY extracts JSON from markdown code blocks (` ```json ` or ` ``` `). If the LLM returns:
- Raw JSON without markdown wrapping
- JSON with trailing text/explanations
- JSON preceded by introductory text

...the regex fails, and since there's no fallback to parse raw JSON from the full content, ALL samples are lost.

**Missing fallback:** After the regex extraction, if `json_blocks` is empty, `items = []` and the function returns zero samples. There's NO attempt to parse `content` directly as JSON after the first `json.loads()` fails.

---

#### **Issue #3: HIGH — Empty API key causes silent failures (Line 66)**

**Location:** `synthesizer.py:66`

```python
api_key: str = os.environ.get("OPENAI_API_KEY", "")
```

**Problem:** If `OPENAI_API_KEY` is not set, `api_key=""` (empty string). The HTTP client is initialized with this empty key (line 115):

```python
headers={
    "Authorization": f"Bearer {self.config.api_key}",  # "Bearer " with empty key!
}
```

The API call will fail with 401 Unauthorized, BUT this error might be swallowed depending on the HTTP response. Even worse, if using a non-OpenAI endpoint that doesn't validate auth strictly, it might return garbage.

**Config confirms this:** `configs/synth_config.yaml:5` shows `api_key: ""` with a comment saying to use env var instead.

---

#### **Issue #4: MEDIUM — No retry mechanism means transient failures lose data (Line 78)**

**Location:** `synthesizer.py:78` and config line 17

```python
max_retries: int = 0
```

Config comment explicitly states: `# No retry mechanism — a known limitation`

**Problem:** Any transient network error, rate limit (429), or timeout causes permanent sample loss. The error is logged but the chunk is never retried.

---

#### **Issue #5: MEDIUM — Validation length filters silently reject (Line 293-297)**

**Location:** `synthesizer.py:293-297`

```python
output_len = len(item.get("output", ""))
if output_len < self.config.min_response_length:  # Default: 50
    return None  # Silent rejection
if output_len > self.config.max_response_length:  # Default: 2000
    return None  # Silent rejection
```

**Problem:** Samples shorter than 50 chars or longer than 2000 chars are silently dropped with no logging. If the LLM generates brief answers or verbose explanations, they're discarded without trace.

---

### 3. HIDDEN ISSUES DISCOVERED

#### **Hidden Issue #1: No validation statistics tracking**

The `_stats` dict tracks `parse_errors` but NOT validation rejections. You can't tell how many samples were rejected by `_validate_sample()`.

#### **Hidden Issue #2: Source directory default doesn't match test data location**

Default config: `source_dir: str = "./data/chunks"` (line 81)
Test data exists at: `nopua/benchmark/test-project/data/chunks/test.txt`

If running from project root without specifying `source_dir`, it looks in wrong location.

#### **Hidden Issue #3: No minimum chunk count validation**

The code logs "No source chunks found" but continues anyway, returning empty list. No warning that pipeline produced nothing due to missing input.

#### **Hidden Issue #4: Missing Content-Type header handling for some APIs**

Some LLM APIs require specific content types or user agents. The httpx client has no customization for this.

---

### 4. RECOMMENDED FIXES

| Priority | Fix | Location |
|----------|-----|----------|
| **P0** | Add fallback JSON parsing after markdown regex fails - try parsing entire `content` as JSON object/array | Line 262-275 |
| **P0** | Add logging when samples are rejected by validation - include reason (missing field, too short, too long) | Line 288-297 |
| **P1** | Validate API key at initialization and fail fast with clear error if missing | Line 105-119 |
| **P1** | Implement retry logic for transient errors (429, 5xx, timeouts) | Line 213-232 |
| **P2** | Track validation rejection stats separately from parse errors | Line 120-125 |
| **P2** | Improve prompt to explicitly require valid JSON array format with exact field names | Line 40-51 |

---

### 5. INVESTIGATION STEPS TAKEN

1. **Read both synthesizer.py files** (nopua/ and benchmark/ versions) - confirmed identical
2. **Read config file** (synth_config.yaml) - found empty API key
3. **Read test chunk file** - verified source data exists
4. **Traced data flow**: `_read_source_chunks()` → `_generate_from_chunk()` → API call → `_parse_samples()` → `_validate_sample()` → `_save_results()`
5. **Analyzed each transformation point** for silent failure modes
6. **Cross-referenced config values** with code defaults
7. **Searched for required_fields usage** to understand validation logic

---

### 6. TOOLS USED

- `Read` - File contents analysis (synthesizer.py ×2, config, test data)
- `Glob` - Pattern matching for config/test files
- `Grep` - Code pattern search for validation logic
- Manual code tracing and logical analysis

---

### 7. VERIFICATION

**Findings verified by:**
- ✅ Reading actual source code (324 lines analyzed)
- ✅ Cross-checking config vs code defaults
- ✅ Tracing complete execution path
- ✅ Identifying specific line numbers for each issue

**Not verified by execution:**
- ❌ Cannot run the synthesizer (no OPENAI_API_KEY set in environment)
- ❌ Cannot observe actual LLM responses to confirm parsing failures

**Recommended verification:**
```bash
# Run with debug logging to see what's happening
export OPENAI_API_KEY="your-key"
python -c "
from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig
import logging
logging.basicConfig(level=logging.DEBUG)

config = SynthConfig(
    api_key='your-key',
    source_dir='./nopua/benchmark/test-project/data/chunks/',
    output_path='./test_output.jsonl'
)
synth = DataSynthesizer(config)
samples = synth.generate()
print(f'Generated {len(samples)} samples')
print(f'Stats: {synth.get_stats()}')
"
```

---

### SUMMARY TABLE

| Category | Count |
|----------|-------|
| **Critical Issues** | 2 (JSON parsing fallback, silent validation rejection) |
| **High Priority** | 1 (Empty API key) |
| **Medium Priority** | 2 (No retries, length filter silence) |
| **Hidden Issues** | 4 (Stats gaps, path mismatches, etc.) |
| **Total Distinct Bugs** | **8** |

**Most likely root cause of "0 samples":** The LLM returns JSON wrapped in markdown OR with introductory text, the regex extraction fails to capture it, and there's no fallback to parse raw content → `items = []` → zero samples pass validation → empty output file.
