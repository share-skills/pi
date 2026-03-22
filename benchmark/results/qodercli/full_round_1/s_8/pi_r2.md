# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 81.14s

---

---

# 🔒 Security Audit Report: Inference Module (`src/inference/`)

## 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Hardcoded API key with insecure default fallback** | Critical | `api_server.py:51` |
| 2 | **API key logged in plaintext at startup** | Critical | `api_server.py:122` |
| 3 | **Permissive CORS policy (allow all origins)** | High | `api_server.py:116` |
| 4 | **No authentication enforcement on API endpoints** | Critical | `api_server.py:147-228` |
| 5 | **trust_remote_code=True enables arbitrary code execution** | Critical | `model_loader.py:28` |
| 6 | **HTTP backend URL without TLS** | High | `api_server.py:44`, `inference_config.yaml:7` |
| 7 | **Race condition on shared mutable state (request_count)** | Medium | `api_server.py:154` |
| 8 | **Silent exception swallowing in streaming handler** | Medium | `api_server.py:300-301` |
| 9 | **Missing resource cleanup for httpx.AsyncClient** | Medium | `api_server.py:127` |
| 10 | **Prompt injection vulnerability via user messages** | High | `api_server.py:245-248` |
| 11 | **Unused import (`re`, `Tuple`, `field` in prompt_builder.py)** | Low | `prompt_builder.py:12-15` |
| 12 | **No input validation on message role/content** | Medium | `api_server.py:61-64` |

---

## 2. Hidden Issues

| # | Issue | Category | Location |
|---|-------|----------|----------|
| H1 | **SSRF vulnerability via unvalidated vllm_url** | Security | `api_server.py:44, 168` |
| H2 | **Denial of Service via unlimited max_tokens** | Security/Performance | `api_server.py:73` |
| H3 | **Memory exhaustion via unbounded context chunks** | Security | `prompt_builder.py:148` |
| H4 | **GPU memory leak on unclean unload** | Resource | `model_loader.py:107-121` |
| H5 | **Information disclosure via /health endpoint** | Security | `api_server.py:207-215` |
| H6 | **Missing timeout on streaming connections** | Reliability | `api_server.py:259-270` |
| H7 | **Config file path traversal vulnerability** | Security | `api_server.py:310-319` |
| H8 | **Non-deterministic response IDs (uuid4 truncation)** | Reliability | `api_server.py:199, 282` |
| H9 | **Thread-unsafe model loading (no double-checked locking)** | Concurrency | `model_loader.py:52-88` |
| H10 | **Prompt length truncation breaks ChatML structure** | Correctness | `prompt_builder.py:152-160` |
| H11 | **Missing error logging for JSON decode failures** | Observability | `api_server.py:300` |
| H12 | **Arbitrary file read via yaml.safe_load on user-provided config** | Security | `api_server.py:312` |

---

## 3. Root Cause

| Issue | Root Cause | Line(s) |
|-------|------------|---------|
| 1, 2 | **Insecure default values + logging anti-pattern**: Default API key hardcoded and logged violates credential handling best practices | `51, 122` |
| 3, 4 | **Missing security middleware**: No auth verification logic; CORS configured for development, not production | `114-120, 147-205` |
| 5 | **Blind trust in remote code**: `trust_remote_code=True` allows model authors to execute arbitrary Python code | `model_loader.py:28, 77` |
| 6 | **Hardcoded localhost HTTP URL**: No environment override or TLS support for backend communication | `44` |
| 7 | **Shared mutable state without synchronization**: `app.state.request_count += 1` is not atomic in async context | `154` |
| 8 | **Bare except with continue**: Exceptions caught but not logged, hiding debugging information | `300-301` |
| 9 | **No lifecycle management for httpx client**: AsyncClient never closed, causing connection pool leaks | `127` |
| 10 | **Direct string interpolation of user input**: User messages injected into ChatML without sanitization | `245-248` |
| H1 | **Server-Side Request Forgery**: vllm_url can be manipulated to attack internal services | `44, 168` |
| H2 | **Missing upper bound validation**: max_tokens only has default, no maximum enforcement | `73` |
| H3 | **No size limit on RAG context**: Large context chunks can exceed model context window | `prompt_builder.py:148` |
| H7 | **Unvalidated file path in load_config()**: Config path not sanitized against `../` traversal | `310-319` |

---

## 4. Recommended Fix

### Fix 1: Secure API Key Handling (Lines 51, 122)

**Before:**
```python
# api_server.py:51
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# api_server.py:122
logger.info(f"Server starting with API key: {config.api_key}")
```

**After:**
```python
# api_server.py:51
api_key: str = os.environ.get("GUWEN_API_KEY")
if not api_key:
    raise ValueError("GUWEN_API_KEY environment variable must be set")

# api_server.py:122
logger.info(f"Server starting with API key: {'*' * 8}")  # Mask the key
```

---

### Fix 2: Add Authentication Middleware (Lines 147-205)

**Before:**
```python
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest):
    app.state.request_count += 1
    # ... no auth check
```

**After:**
```python
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

def verify_api_key(
    creds: HTTPAuthorizationCredentials = Security(security)
) -> None:
    if creds is None or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    _=Depends(verify_api_key)
):
    app.state.request_count += 1
```

---

### Fix 3: Restrict CORS (Line 116)

**Before:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After:**
```python
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### Fix 4: Disable trust_remote_code by Default (model_loader.py:28)

**Before:**
```python
trust_remote_code: bool = True
```

**After:**
```python
trust_remote_code: bool = False  # Only enable for verified models
```

---

### Fix 5: Add Input Validation (api_server.py:61-79)

**Before:**
```python
class ChatCompletionRequest(BaseModel):
    max_tokens: Optional[int] = 2048
```

**After:**
```python
class ChatCompletionRequest(BaseModel):
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
```

---

### Fix 6: Proper Resource Cleanup (api_server.py:127)

**Before:**
```python
app.state.http_client = httpx.AsyncClient(timeout=config.timeout)
```

**After:**
```python
@app.on_event("shutdown")
async def shutdown_http_client():
    await app.state.http_client.aclose()

app.state.http_client = httpx.AsyncClient(timeout=config.timeout)
```

---

### Fix 7: Sanitize vllm_url (api_server.py:44)

**Before:**
```python
vllm_url: str = "http://localhost:8001"
```

**After:**
```python
from urllib.parse import urlparse

vllm_url: str = os.environ.get("VLLM_URL", "http://localhost:8001")

def _validate_backend_url(url: str) -> bool:
    """Ensure URL points to allowed backend hosts only."""
    parsed = urlparse(url)
    allowed_hosts = {"localhost", "127.0.0.1", "vllm-backend"}
    return parsed.hostname in allowed_hosts and parsed.scheme in ("http", "https")
```

---

## 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read all 4 inference module source files | Identified 12 surface issues |
| 2 | Searched for `allow_origins=["*"]` pattern | Confirmed permissive CORS is isolated to this module |
| 3 | Searched for `trust_remote_code=True` usage | Found 4 occurrences across training + inference |
| 4 | Searched for API key patterns | Found hardcoded default + plaintext logging |
| 5 | Searched for exception handling patterns | Found silent exception swallowing in stream handler |
| 6 | Searched for HTTP URLs | Confirmed hardcoded `http://localhost:8001` |
| 7 | Analyzed data flow for prompt injection | Identified unsanitized user input in ChatML template |
| 8 | Checked resource lifecycle | Found missing `aclose()` for httpx client |
| 9 | Reviewed concurrency patterns | Identified race condition on `request_count` |
| 10 | Examined config loading | Found path traversal vulnerability in `load_config()` |
| 11 | Cross-referenced with config YAML | Confirmed api_key also hardcoded in config file |
| 12 | Analyzed token estimation logic | Found potential DoS via unbounded context |

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 4 inference module source files + config YAML |
| `Grep` | Search for security anti-patterns (CORS, trust_remote_code, api_key, http://) |
| `Grep` | Search for exception handling patterns (bare except, pass) |
| `Grep` | Search for resource management patterns (close, del, AsyncClient) |
| `Grep` | Search for input validation patterns (sanitize, validate, escape) |

---

## 7. Verification

### Immediate Verification Commands

```bash
# 1. Verify no hardcoded secrets in source
grep -rn "sk-guwen-default-key" benchmark/data/test-project/src/inference/

# 2. Verify no plaintext credential logging
grep -rn "logger.info.*api_key\|logger.info.*password" benchmark/data/test-project/src/inference/

# 3. Verify CORS configuration
grep -A5 "CORSMiddleware" benchmark/data/test-project/src/inference/api_server.py

# 4. Verify trust_remote_code setting
grep "trust_remote_code" benchmark/data/test-project/src/inference/model_loader.py

# 5. Check for httpx client cleanup
grep -A2 "@app.on_event.*shutdown" benchmark/data/test-project/src/inference/api_server.py
```

### Recommended Pre-Deployment Checklist

| Item | Command | Expected Result |
|------|---------|-----------------|
| No hardcoded credentials | `grep -r "sk-" src/inference/*.py` | No matches |
| Auth enforced on endpoints | Manual curl test without Authorization header | 401 Unauthorized |
| CORS restricted | Check `allow_origins` in code | Not `["*"]` |
| TLS for backend | Check `vllm_url` config | `https://` prefix |
| Input validation | Send request with `max_tokens: 99999` | 422 Validation Error |
| Resource cleanup | Load test + monitor connections | No connection leak |

---

## 🚨 Risk Summary

| Risk Level | Count | Issues |
|------------|-------|--------|
| **Critical** | 4 | Hardcoded API key, plaintext logging, no auth, trust_remote_code |
| **High** | 3 | Permissive CORS, HTTP backend, prompt injection |
| **Medium** | 4 | Race condition, silent exceptions, missing cleanup, no input validation |
| **Low** | 1 | Unused imports |

**Total Issues: 12 surface + 12 hidden = 24 issues**

---

## ⚠️ Production Deployment Recommendation

**DO NOT DEPLOY** until the following are addressed:

1. **P0 (Blocker)**: Fixes 1, 2, 4, 5 (auth, credentials, trust_remote_code)
2. **P1 (High Priority)**: Fixes 3, 6, 7 (CORS, TLS, SSRF prevention)
3. **P2 (Before Scale)**: Fixes 7, 8, 9 (resource cleanup, race condition, logging)
