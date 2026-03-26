# Scenario 4: API Server Response Format Mismatch
## Condition: pi | Run: 1
## Duration: 127.81s

---

Now I have all the information needed. Let me compile the comprehensive investigation report:

---

## 🧠 PI · Investigation Complete · API Server Response Format Mismatch

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **`finish_reason` type too permissive** - uses `str` instead of `Literal["stop", "length", "tool_calls", "content_filter", "function_call"]` | 🔴 CRITICAL | `api_server.py:86` |
| 2 | **`ChatMessage.role` too permissive** - uses `str` instead of `Literal["system", "user", "assistant", "tool"]` for response messages | 🟡 HIGH | `api_server.py:63` |
| 3 | **`UsageInfo` field order mismatch** - OpenAI SDK expects `completion_tokens` first, not `prompt_tokens` first | 🟡 MODERATE | `api_server.py:89-93` |
| 4 | **Missing `service_tier` field** in `ChatCompletionResponse` | ⚪ LOW | `api_server.py:96-107` |
| 5 | **Missing `system_fingerprint` field** in `ChatCompletionResponse` | ⚪ LOW | `api_server.py:96-107` |
| 6 | **vLLM `finish_reason` passthrough without normalization** - vLLM may return `"eos_token"`, `"max_tokens"` which don't match OpenAI literals | 🔴 CRITICAL | `api_server.py:203` |
| 7 | **Streaming chunk missing `finish_reason` normalization** - same issue as #6 for streaming responses | 🔴 CRITICAL | `api_server.py:311-313` |

### 2. Hidden Issues (Beyond User's Ask)

| # | Issue | Category | Location |
|---|-------|----------|----------|
| A | **API key logged at startup** - secrets exposure in logs | Security | `api_server.py:130` |
| B | **No authentication middleware** - `/v1/chat/completions` accepts requests without auth | Security | `api_server.py:155-224` |
| C | **CORS allows all origins with credentials** - security misconfiguration | Security | `api_server.py:122-127` |
| D | **Silent exception handling in streaming** - JSON parse errors silently skipped | Error Handling | `api_server.py:319-320` |
| E | **HTTP client never closed** - resource leak, no shutdown handler | Resource Management | `api_server.py:135` |
| F | **No retry logic for transient backend failures** | Reliability | `api_server.py:174-192` |
| G | **Unused import** - `datetime` imported but never used | Code Quality | `api_server.py:22` |
| H | **Missing `logprobs` field** in `ChatCompletionChoice` for OpenAI compatibility | Compatibility | `api_server.py:82-86` |
| I | **Hardcoded vLLM URL without TLS support** | Security/Config | `api_server.py:44` |

### 3. Root Cause

**Primary Root Cause:** The pydantic models were designed based on **documentation snapshots** rather than the **actual OpenAI SDK source code**. The OpenAI SDK uses:

1. **Strict `Literal` types** for enum-like fields that enforce exact string values at the type level:
   - `ChatCompletionMessage.role`: `Literal["assistant"]` (for responses)
   - `Choice.finish_reason`: `Literal["stop", "length", "tool_calls", "content_filter", "function_call"]`
   - `ChatCompletion.object`: `Literal["chat.completion"]`

2. **Specific field ordering** in `CompletionUsage`:
   - OpenAI SDK: `completion_tokens` → `prompt_tokens` → `total_tokens`
   - Current code: `prompt_tokens` → `completion_tokens` → `total_tokens`

3. **Evolving schema** with optional fields like `service_tier`, `system_fingerprint`, `logprobs` added over time

**Additionally**, the code **proxies vLLM responses directly** without normalizing vLLM-specific values to OpenAI-compatible values:
- vLLM returns `"eos_token"` → OpenAI expects `"stop"`
- vLLM returns `"max_tokens"` → OpenAI expects `"length"`

**Initially I thought** the issue was just about the `created` field type (based on the scenario description mentioning "string instead of int"). **Upon closer inspection**, the `created` field is actually correctly defined as `int` and uses `int(time.time())`. The actual root causes are:
1. Missing `Literal` type constraints
2. Field order mismatch in `UsageInfo`
3. Missing optional fields expected by newer SDK versions
4. vLLM value normalization gap

**Actually**, the problem is deeper: even if the model definitions were fixed, the vLLM passthrough would still cause validation failures when vLLM returns non-standard `finish_reason` values.

### 4. Recommended Fix

#### Fix 1: Update Pydantic Models with Literal Types

```python
# api_server.py: Lines 16-23, 61-107

from typing import List, Dict, Optional, Any, Union, Literal  # Add Literal

class ChatMessage(BaseModel):
    """A single message in the chat history."""
    role: Literal["system", "user", "assistant", "tool"]  # Constrained roles
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "function_call"]
    logprobs: Optional[Dict[str, Any]] = None  # Add for OpenAI compatibility


class UsageInfo(BaseModel):
    """Token usage information matching OpenAI SDK field order."""
    completion_tokens: int  # Field order matters - must be first
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[Dict[str, Any]] = None
    prompt_tokens_details: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str
    object: Literal["chat.completion"] = "chat.completion"  # Constrained
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    service_tier: Optional[Literal["auto", "default", "flex", "scale", "priority"]] = None
    system_fingerprint: Optional[str] = None
    usage: Optional[UsageInfo] = None
```

#### Fix 2: Add finish_reason Normalization Function

```python
# api_server.py: Add after line 32 (after logger definition)

FINISH_REASON_MAP = {
    "stop": "stop",
    "eos_token": "stop",
    "length": "length",
    "max_tokens": "length",
    "tool_calls": "tool_calls",
    "function_call": "function_call",
    "content_filter": "content_filter",
}


def _normalize_finish_reason(reason: str) -> str:
    """Normalize vLLM finish reason to OpenAI format."""
    return FINISH_REASON_MAP.get(reason, "stop")
```

#### Fix 3: Apply Normalization in Response Construction

```python
# api_server.py: Line 203

# Before:
finish_reason=choice.get("finish_reason", "stop"),

# After:
finish_reason=_normalize_finish_reason(choice.get("finish_reason", "stop")),
```

#### Fix 4: Apply Normalization in Streaming Response

```python
# api_server.py: Lines 311-313

# Before:
"finish_reason": chunk["choices"][0].get("finish_reason"),

# After:
"finish_reason": _normalize_finish_reason(
    chunk["choices"][0].get("finish_reason")
),
```

#### Fix 5: Remove Unused Import

```python
# api_server.py: Line 22

# Before:
from datetime import datetime

# After:
# (remove this line entirely)
```

#### Fix 6: Remove API Key from Logs

```python
# api_server.py: Line 130

# Before:
logger.info(f"Server starting with API key: {config.api_key}")
logger.info(f"vLLM backend: {config.vllm_url}")

# After:
logger.info(f"Server starting on {config.host}:{config.port}")
logger.info(f"vLLM backend configured")
```

#### Fix 7: Add HTTP Client Shutdown Handler

```python
# api_server.py: Add after line 136

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()
```

### 5. Steps Taken

1. **Read `api_server.py` completely** (lines 1-364) to understand current implementation
2. **Fetched OpenAI SDK source code** from GitHub:
   - `ChatCompletion` model - confirmed `created: int`, `object: Literal["chat.completion"]`
   - `Choice.finish_reason` - confirmed `Literal["stop", "length", "tool_calls", "content_filter", "function_call"]`
   - `ChatCompletionMessage.role` - confirmed `Literal["assistant"]` for responses
   - `CompletionUsage` - confirmed field order: `completion_tokens` first
3. **Compared field-by-field** between api_server.py and OpenAI SDK source
4. **Identified mismatches** in type constraints, field ordering, and missing fields
5. **Performed security scan** checking for secret exposure, missing auth, CORS issues
6. **Read test file** (`test_api_server.py`) to understand expected validations
7. **Initial assumption**: Only `created` field type was wrong (based on scenario description)
8. **Upon closer inspection**: The `created` field is actually correct; the real issues are `Literal` types and vLLM normalization
9. **Expanded scope** to check streaming response for same issues - found identical problem at line 311

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read api_server.py source code line by line |
| `Grep` | Search for specific patterns (finish_reason, usage, created) |
| `WebFetch` | Retrieve actual pydantic model definitions from openai-python GitHub repo |
| `Glob` | Locate test files for context |

### 7. Verification

**Verification Commands:**

```bash
# 1. Verify pydantic model definitions after fix
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python3 -c "
from src.inference.api_server import ChatCompletionResponse, ChatCompletionChoice, ChatMessage, UsageInfo
import inspect

# Check Literal types
print('Checking ChatMessage.role annotation...')
role_annotation = ChatMessage.model_fields['role'].annotation
print(f'  role type: {role_annotation}')

print('Checking ChatCompletionChoice.finish_reason annotation...')
finish_annotation = ChatCompletionChoice.model_fields['finish_reason'].annotation
print(f'  finish_reason type: {finish_annotation}')

print('Checking UsageInfo field order...')
fields = list(UsageInfo.model_fields.keys())
print(f'  field order: {fields}')
assert fields[0] == 'completion_tokens', 'completion_tokens must be first'

print('Checking ChatCompletionResponse fields...')
response_fields = list(ChatCompletionResponse.model_fields.keys())
print(f'  response fields: {response_fields}')
assert 'service_tier' in response_fields, 'Missing service_tier'
assert 'system_fingerprint' in response_fields, 'Missing system_fingerprint'

print('All checks passed!')
"

# 2. Verify finish_reason normalization function exists
python3 -c "
from src.inference.api_server import _normalize_finish_reason, FINISH_REASON_MAP

# Test normalization
assert _normalize_finish_reason('eos_token') == 'stop'
assert _normalize_finish_reason('max_tokens') == 'length'
assert _normalize_finish_reason('stop') == 'stop'
print('finish_reason normalization works correctly')
"

# 3. Run existing tests
pytest tests/test_api_server.py -v

# 4. Test with OpenAI SDK (if available)
python3 -c "
from openai import OpenAI
from src.inference.api_server import create_app, InferenceConfig
from fastapi.testclient import TestClient

config = InferenceConfig(vllm_url='http://mock-vllm:8001')
app = create_app(config)
client = TestClient(app)

# Mock a proper vLLM response
import json
mock_response = {
    'id': 'cmpl-test',
    'object': 'text_completion',
    'created': 1234567890,
    'model': 'guwen-llm-7b-chat',
    'choices': [{
        'text': '學而時習之',
        'finish_reason': 'stop',
        'logprobs': None
    }],
    'usage': {
        'prompt_tokens': 10,
        'completion_tokens': 20,
        'total_tokens': 30
    }
}

with patch('httpx.AsyncClient.post') as mock_post:
    mock_response_obj = MagicMock()
    mock_response_obj.json.return_value = mock_response
    mock_response_obj.raise_for_status = MagicMock()
    mock_post.return_value = mock_response_obj
    
    response = client.post(
        '/v1/chat/completions',
        json={
            'model': 'guwen-llm-7b-chat',
            'messages': [{'role': 'user', 'content': 'hello'}]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate with OpenAI SDK
    from openai.types.chat import ChatCompletion
    completion = ChatCompletion(**data)
    print(f'OpenAI SDK validation passed: {completion.id}')
"
```

**Manual Verification Steps:**
- Check `api_server.py:61-64` after fix to ensure `role` uses `Literal` type
- Check `api_server.py:82-86` after fix to ensure `finish_reason` uses `Literal` type
- Check `api_server.py:89-93` after fix to ensure `completion_tokens` is first field
- Check `api_server.py:96-107` after fix to ensure `service_tier` and `system_fingerprint` are present
- Check `api_server.py:203` and `api_server.py:311-313` use `_normalize_finish_reason()`
- Check `api_server.py:130` does NOT log API key
- Check `api_server.py:22` does NOT import `datetime`

---

### 📋 Delivery Confirmation

□ **目標匹配**: API response format mismatch → Root cause identified (Literal types + field order + vLLM normalization)  
□ **邊界覆蓋**: Type constraints, field ordering, missing fields, security issues, resource leaks  
□ **風險可控**: Fix requires code changes; recommend testing with actual OpenAI SDK client before deployment
