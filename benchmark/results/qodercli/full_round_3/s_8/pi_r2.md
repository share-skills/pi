# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 32.12s

---

Now let me conduct a systematic security audit following the PI protocol. I'll examine each file for security issues across multiple dimensions.

## Security Audit Results

### 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `api_server.py` | 36 | **Hardcoded default API key** - Falls back to insecure default if env var not set |
| 2 | `api_server.py` | 85-89 | **CORS wildcard `*`** - Allows any origin with credentials, enabling CSRF attacks |
| 3 | `api_server.py` | 107-108 | **No API key authentication** - Endpoint doesn't validate the API key |
| 4 | `api_server.py` | 146 | **Missing input validation** - User-controlled `stop` parameter passed directly to backend |
| 5 | `api_server.py` | 238 | **Bare except in JSON parsing** - Silently catches all exceptions during stream parsing |
| 6 | `model_loader.py` | 22 | **`trust_remote_code=True`** - Executes arbitrary code from model repository |
| 7 | `model_loader.py` | 17 | **No path validation** - Model path not validated for path traversal |
| 8 | `prompt_builder.py` | 120 | **Prompt injection vulnerability** - User text injected without sanitization |

---

### 2. Hidden Issues

| # | File | Line | Category | Issue |
|---|------|------|----------|-------|
| 1 | `api_server.py` | 92 | Resource Leak | `httpx.AsyncClient` never closed (no `__del__` or shutdown handler) |
| 2 | `api_server.py` | 96 | Thread Safety | `app.state.request_count += 1` has race condition in async context |
| 3 | `api_server.py` | 133 | Error Handling | HTTPError exception message logged but not returned - info leakage risk |
| 4 | `api_server.py` | 238 | Security | Exception caught but error type hidden - could mask attack attempts |
| 5 | `api_server.py` | 256 | Input Validation | Config file path not validated - potential path traversal |
| 6 | `model_loader.py` | 56 | Resource Management | `unload()` uses `del` but no guarantee of immediate GPU memory release |
| 7 | `model_loader.py` | 17 | Configuration | Default model path is relative - deployment fragility |
| 8 | `prompt_builder.py` | 94 | Boundary Condition | No minimum length check on truncation - could truncate to empty |
| 9 | `prompt_builder.py` | 120 | Injection | Context chunks from RAG not sanitized - secondary injection vector |
| 10 | `__init__.py` | N/A | Unused Import | `model_loader` module imported nowhere but exists |

---

### 3. Root Cause

| Root Cause | Files Affected | Explanation |
|------------|----------------|-------------|
| **Insecure defaults** | `api_server.py:36` | API key defaults to hardcoded value instead of requiring explicit configuration |
| **Missing auth middleware** | `api_server.py:107` | No dependency injection for API key validation on protected endpoints |
| **Overly permissive CORS** | `api_server.py:85-89` | Wildcard origin with `allow_credentials=True` violates CORS security |
| **Blind trust in external code** | `model_loader.py:22` | `trust_remote_code=True` allows model authors to execute arbitrary code |
| **No input sanitization** | `api_server.py:146`, `prompt_builder.py:120` | User input passed directly to backend/prompt without validation |
| **Missing lifecycle management** | `api_server.py:92` | No shutdown handler to close HTTP client connections |
| **Non-atomic operations on shared state** | `api_server.py:96` | Async increment without lock protection |

---

### 4. Recommended Fix

#### Fix 1: Secure API Key Configuration (`api_server.py:36`)
```python
# Before (insecure):
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# After (secure):
api_key: str = os.environ.get("GUWEN_API_KEY")
if not self.api_key:
    raise ValueError("GUWEN_API_KEY environment variable must be set")
```

#### Fix 2: Restrict CORS (`api_server.py:85-89`)
```python
# Before (insecure):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # ⚠️ Incompatible with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# After (secure):
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Restrict to needed methods
    allow_headers=["Authorization", "Content-Type"],
)
```

#### Fix 3: Add Authentication Middleware (`api_server.py`)
```python
# Add new dependency for auth:
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Verify API key from Authorization header."""
    expected_key = app.state.config.api_key
    if credentials.credentials != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Apply to endpoints:
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completion(request: ChatCompletionRequest):
    ...
```

#### Fix 4: Disable Remote Code Trust (`model_loader.py:22`)
```python
# Before (risky):
trust_remote_code: bool = True

# After (secure):
trust_remote_code: bool = False  # Only load models with local code
```

#### Fix 5: Add Input Validation (`api_server.py:146`)
```python
# Add validation before passing to backend:
def _validate_stop_parameter(stop: Optional[Union[str, List[str]]]) -> None:
    """Validate stop parameter to prevent injection."""
    if stop is None:
        return
    if isinstance(stop, str):
        stop = [stop]
    for s in stop:
        if len(s) > 100:  # Reasonable limit
            raise HTTPException(status_code=400, detail="Stop token too long")
        if any(c in s for c in ["
