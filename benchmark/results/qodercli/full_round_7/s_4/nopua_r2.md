# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 2
## Duration: 138.78s

---

Now I have a clear picture. Let me analyze the issues in the code:

## Investigation Summary

### Issues Found

**1. CRITICAL: `created` field type mismatch (Line 97, 200, 284)**
- **Current code**: `created: str` in model definition (line 97), uses `datetime.now().isoformat()` (lines 200, 284)
- **OpenAI spec requires**: `created: int` - Unix timestamp in **seconds**
- **Impact**: OpenAI SDK Pydantic validation fails with `ValidationError` because it expects `int`, receives `str`

**2. MISSING: `usage` field not always included in response**
- **Current code**: `usage: Optional[UsageInfo] = None` (line 101) - only populated when vLLM returns usage
- **OpenAI spec**: While technically optional, many SDK clients expect `usage` to be present for token tracking
- **Impact**: May cause issues with SDK clients that assume `usage` exists

**3. MISSING: `logprobs` field in `ChatCompletionChoice`**
- **Current code**: `ChatCompletionChoice` (lines 82-86) has no `logprobs` field
- **OpenAI spec**: `Choice` should include `logprobs: Optional[ChatCompletionTokenLogprob]`
- **Impact**: SDK may fail validation if it expects this field structure

**4. STREAMING BUG: Stream chunk reuses request model name incorrectly (Line 285)**
- **Current code**: Uses `request.model` which is the client's requested model name
- **Should use**: `config.model_name` for consistency with non-streaming path (line 201)

**5. HIDDEN ISSUE: UsageInfo missing details fields**
- **Current code**: Simple 3-field `UsageInfo` (lines 91-94 in original reference)
- **OpenAI 2026 spec**: Includes optional `completion_tokens_details` and `prompt_tokens_details`
- **Impact**: May cause validation issues with newer SDK versions expecting these fields

---

### Root Cause

The code was written with incorrect assumptions about the OpenAI API schema:
1. `created` field uses ISO 8601 datetime string instead of Unix timestamp integer
2. Several optional but expected fields are missing from response models

---

### Recommended Fixes

```python
# Fix 1: ChatCompletionResponse.created must be int (Unix timestamp seconds)
class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int  # Changed from str to int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[UsageInfo] = None

# Fix 2: Generate timestamp correctly (lines 198-203)
response = ChatCompletionResponse(
    id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
    created=int(time.time()),  # Changed from datetime.now().isoformat()
    model=request.model,
    choices=choices,
    usage=usage,
)

# Fix 3: Streaming chunk timestamp (line 284)
chat_chunk = {
    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
    "object": "chat.completion.chunk",
    "created": int(time.time()),  # Changed from datetime.now().isoformat()
    "model": request.model,
    ...
}
```

---

### Steps Taken

1. Read the full `api_server.py` source file
2. Searched OpenAI API reference documentation for response schema
3. Fetched the official `openai-python` SDK source code to verify exact field types
4. Cross-referenced vLLM response format expectations
5. Compared current implementation against OpenAI spec

---

### Tools Used

- `Read` - File reading
- `WebSearch` - Search queries for OpenAI schema
- `WebFetch` - Fetch official OpenAI Python SDK source code

---

### Verification

I verified findings by:
1. Confirming `ChatCompletion.created` type is `int` in the official openai-python SDK source
2. Confirming the value should be "Unix timestamp (in seconds)" per API docs
3. Identifying all three locations where the bug manifests (model definition + two generation sites)
