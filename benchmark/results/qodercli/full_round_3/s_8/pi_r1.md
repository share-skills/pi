# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 33.8s

---

The user provided the source files inline in their request. Let me analyze the code they provided directly.

---

# Security Audit Report: Inference Module

## 1. Issues Found

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔴 Blocker | Hardcoded default API key with weak value | `api_server.py:37` |
| 2 | 🔴 Blocker | CORS allows all origins (`*`) with credentials | `api_server.py:82-86` |
| 3 | 🔴 Blocker | No authentication enforcement on endpoints | `api_server.py:95-175` |
| 4 | 🟡 Suggestion | `trust_remote_code=True` enables arbitrary code execution | `model_loader.py:29` |
| 5 | 🟡 Suggestion | Default system prompt could be overridden via injection | `prompt_builder.py:78-82` |
| 6 | 🟡 Suggestion | No rate limiting on inference endpoints | `api_server.py:95` |
| 7 | 🟡 Suggestion | API key logged at startup (information leakage) | `api_server.py:89` |
| 8 | 🟡 Suggestion | No input validation on `max_tokens`, `temperature` ranges | `api_server.py:52-60` |
| 9 | 🟡 Suggestion | Embedding endpoint proxies arbitrary JSON without validation | `api_server.py:183-191` |
| 10 | 🟡 Suggestion | Stream completion yields error chunks without sanitization | `api_server.py:230-234` |

---

## 2. Hidden Issues

| # | Category | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔒 Security | Environment variable fallback allows deployment with weak key | `api_server.py:37` |
| 2 | 🔒 Security | No HTTPS enforcement for production deployment | Entire module |
| 3 | 🔒 Security | Request body size not limited (DoS vector) | `api_server.py:95` |
| 4 | ⚡ Performance | `request_count` is unbounded counter (memory leak over time) | `api_server.py:91` |
| 5 | ⚡ Performance | HTTP client never closed (connection pool leak) | `api_server.py:92` |
| 6 | 📖 Readability | `created` field uses ISO format instead of Unix timestamp (OpenAI incompatibility) | `api_server.py:66, 153` |
| 7 | ✅ Correctness | `_stream_completion` doesn't increment request count | `api_server.py:214` |
| 8 | ✅ Correctness | Streaming error handling yields partial data without proper SSE format | `api_server.py:230-234` |
| 9 | 🔒 Security | Model path is hardcoded and not validated for path traversal | `model_loader.py:24` |
| 10 | 🔒 Security | `torch.cuda.empty_cache()` may fail silently on non-CUDA systems | `model_loader.py:102-107` |

---

## 3. Root Cause

### Primary Security Issues

**1. Weak Authentication (api_server.py:37)**
```python
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")
```
- Default key is predictable and documented in source code
- No validation that a strong key is provided before deployment

**2. Permissive CORS (api_server.py:82-86)**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Any origin can access API
    allow_credentials=True,  # Cookies/auth headers allowed
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- Combined `allow_origins=["*"]` + `allow_credentials=True` is dangerous
- Allows any website to make authenticated requests on behalf of users

**3. Missing Auth Enforcement (api_server.py:95-175)**
- The `api_key` is configured but **never checked** on any endpoint
- Anyone can call `/v1/chat/completions` without authentication

**4. Remote Code Execution Risk (model_loader.py:29)**
```python
trust_remote_code: bool = True
```
- vLLM will execute arbitrary code from model repository
- Compromised model repo = RCE on inference server

---

## 4. Recommended Fix

### Fix 1: Enforce Strong API Key

```python
# api_server.py:37
@dataclass
class InferenceConfig:
    # ...
    api_key: str = os.environ.get("GUWEN_API_KEY")
    
    def __post_init__(self):
        if not self.api_key or len(self.api_key) < 32:
            raise ValueError(
                "GUWEN_API_KEY must be set and at least 32 characters. "
                "Generate with: openssl rand -hex 32"
            )
```

### Fix 2: Restrict CORS Origins

```python
# api_server.py:82-86
def create_app(config: InferenceConfig = None) -> FastAPI:
    config = config or InferenceConfig()
    
    # Determine allowed origins from environment
    allowed_origins = os.environ.get(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8080"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Explicit list only
        allow_credentials=True,
        allow_methods=["POST", "OPTIONS"],  # Only needed methods
        allow_headers=["Authorization", "Content-Type"],
    )
```

### Fix 3: Add Authentication Middleware

```python
# api_server.py: Add after line 88
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    creds: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Verify API key from Authorization header."""
    config: InferenceConfig = app.state.config
    if not creds or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials

# Then protect endpoints:
@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    _: str = Depends(verify_api_key),  # Add auth check
):
    # ... existing implementation
```

### Fix 4: Disable Trust Remote Code

```python
# model_loader.py:29
@dataclass
class ModelConfig:
    # ...
    trust_remote_code: bool = False  # Only load local/safe models
    
    # Add allow_local_only for extra safety
    local_only: bool = True  # Prevent downloading from remote repos
```

### Fix 5: Add Input Validation

```python
# api_server.py:52-60
class ChatCompletionRequest(BaseModel):
    # ...
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=32768)
    n: Optional[int] = Field(default=1, ge=1, le=10)
```

### Fix 6: Close HTTP Client on Shutdown

```python
# api_server.py: Add after line 93
@app.on_event("shutdown")
async def shutdown_http_client():
    await app.state.http_client.aclose()
    logger.info("HTTP client closed")
```

---

## 5. Steps Taken

1. **Read all 4 source files** — Analyzed complete codebase structure
2. **Checked authentication flow** — Traced `api_key` from config → usage (found: never validated)
3. **Examined CORS configuration** — Identified `allow_origins=["*"]` + `allow_credentials=True` anti-pattern
4. **Reviewed model loading** — Found `trust_remote_code=True` enabling arbitrary code execution
5. **Traced request handling** — Discovered no input validation on numeric fields
6. **Checked resource management** — Found HTTP client never closed, request_count unbounded
7. **Analyzed error handling** — Identified unsanitized error output in streaming
8. **Cross-referenced OpenAI spec** — Found `created` field type mismatch (ISO vs Unix timestamp)
9. **Security pattern search** — Looked for common vulnerabilities (injection, path traversal, etc.)
10. **Configuration audit** — Checked all hardcoded values for security implications

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual Code Review | Line-by-line security analysis |
| Pattern Matching | Identified security anti-patterns (CORS, auth, RCE) |
| Data Flow Analysis | Traced config → usage paths |
| OWASP Checklist | Validated against top 10 vulnerabilities |

---

## 7. Verification

**Verification Commands:**

```bash
# 1. Check API key enforcement (should fail without key)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'
# Expected: 401 Unauthorized (after fix)

# 2. Verify CORS restriction
curl -H "Origin: https://evil.com" -X OPTIONS http://localhost:8000/v1/chat/completions
# Expected: No Access-Control-Allow-Origin header for evil.com (after fix)

# 3. Test input validation
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{"messages": [], "temperature": 999}'
# Expected: 422 Validation Error (after fix)

# 4. Check trust_remote_code setting
grep -n "trust_remote_code" src/inference/model_loader.py
# Expected: trust_remote_code: bool = False (after fix)
```

**Pre-fix Status**: All above checks would **FAIL** (no auth, permissive CORS, no validation, trust_remote_code=True).

---

## Summary

| Category | Count |
|----------|-------|
| Blocker Issues | 3 |
| Suggestions | 7 |
| Hidden Issues | 10 |
| Total Findings | 20 |

**Critical Actions Before Production:**
1. Enforce strong API key via environment variable
2. Restrict CORS to explicit origins
3. Add authentication middleware to all endpoints
4. Set `trust_remote_code=False`
5. Add input validation with Pydantic Field constraints
6. Implement HTTP client cleanup on shutdown
