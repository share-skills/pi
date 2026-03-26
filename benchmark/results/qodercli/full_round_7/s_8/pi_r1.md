# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 51.26s

---

## Security Audit Report: Inference Module

Based on my analysis of the provided source files, here is the comprehensive security audit:

---

## 1. Issues Found

| # | Severity | File:Line | Issue |
|---|----------|-----------|-------|
| 1 | 🔴 Blocker | api_server.py:36 | **Hardcoded API key with default fallback** - `api_key` defaults to `"sk-guwen-default-key-2024"` if env var not set |
| 2 | 🔴 Blocker | api_server.py:67-71 | **CORS allows all origins** - `allow_origins=["*"]` permits any website to make requests |
| 3 | 🔴 Blocker | api_server.py:139-140 | **No authentication check** - `/v1/chat/completions` endpoint doesn't validate API key |
| 4 | 🟡 Suggestion | api_server.py:80 | **API key logged at startup** - `logger.info(f"Server starting with API key: {config.api_key}")` exposes secret in logs |
| 5 | 🟡 Suggestion | model_loader.py:26 | **trust_remote_code=True** - Allows arbitrary code execution from model files |
| 6 | 🟡 Suggestion | api_server.py:180-183 | **Embedding endpoint lacks auth** - `/v1/embeddings` proxies without authentication |
| 7 | 🟡 Suggestion | api_server.py:45-52 | **No request size limits** - Missing max body size configuration enables DoS |
| 8 | ⚪ Nit | api_server.py:30 | **Default timeout 120s** - May allow resource exhaustion via slow requests |

---

## 2. Hidden Issues (Beyond Security Ask)

| # | Category | File:Line | Issue |
|---|----------|-----------|-------|
| 9 | Performance | api_server.py:139 | **No rate limiting** - Request counter exists but no throttling logic |
| 10 | Resource Leak | api_server.py:78 | **httpx client never closed** - No shutdown handler to close `app.state.http_client` |
| 11 | Error Handling | api_server.py:168-170 | **Bare exception in streaming** - Generic `except` swallows specific error details |
| 12 | Input Validation | api_server.py:99 | **No message content validation** - Empty/malformed messages not rejected |
| 13 | Input Validation | prompt_builder.py:118 | **Token estimation is inaccurate** - Simple heuristic may cause context overflow |
| 14 | Configuration | api_server.py:36 | **API key not required** - Server runs even with missing/empty key |
| 15 | Thread Safety | api_server.py:79 | **Request counter not atomic** - `app.state.request_count += 1` is not thread-safe |

---

## 3. Root Cause Analysis

### Critical Issues

**Issue #1-3: Authentication Bypass**
- **Root Cause**: The `InferenceConfig` defines an `api_key` field (api_server.py:36), but no middleware or decorator actually enforces authentication on protected endpoints. The API key is logged but never validated.

**Issue #4: Credential Logging**
- **Root Cause**: Debug logging pattern (`logger.info`) includes sensitive configuration values without redaction.

**Issue #5: Remote Code Trust**
- **Root Cause**: `trust_remote_code=True` in vLLM config allows model files to execute arbitrary Python code during loading.

**Issue #6: CORS Misconfiguration**
- **Root Cause**: Wildcard CORS policy (`*`) is permissive by default, allowing any origin to access the API.

---

## 4. Recommended Fixes

### Fix #1: Implement API Key Authentication

```python
# api_server.py - Add authentication middleware
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    config = app.state.config
    if credentials.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Apply to protected endpoints
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest, 
                          _ = Depends(verify_api_key)):  # Add auth dependency
    ...
```

### Fix #2: Restrict CORS Origins

```python
# api_server.py:67-71 - Replace wildcard with explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Explicit list
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Limit methods
    allow_headers=["Authorization", "Content-Type"],
)
```

### Fix #3: Remove Credential Logging

```python
# api_server.py:80 - Redact API key in logs
logger.info(f"Server starting with API key: {'*' * 8}***")
logger.info(f"vLLM backend: {config.vllm_url}")
```

### Fix #4: Require API Key

```python
# api_server.py:36 - Fail if API key not configured
api_key: str = os.environ.get("GUWEN_API_KEY")

def __post_init__(self):
    if not self.api_key or self.api_key == "sk-guwen-default-key-2024":
        raise ValueError("GUWEN_API_KEY environment variable must be set")
```

### Fix #5: Disable Remote Code Trust (If Possible)

```python
# model_loader.py:26 - Only trust remote code if absolutely necessary
trust_remote_code: bool = False  # Set to True only with verified models
```

### Fix #6: Add Request Size Limits

```python
# api_server.py:64 - Add request size limit
app = FastAPI(
    title="Guwen-LLM API",
    description="...",
    version="0.4.2",
)

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=413, detail="Request too large")
    return await call_next(request)
```

### Fix #7: Add Shutdown Handler

```python
# api_server.py:78-79 - Add cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_cleanup():
    await app.state.http_client.aclose()
    logger.info("HTTP client closed")
```

### Fix #8: Add Rate Limiting

```python
# api_server.py - Add rate limiting using slowapi or custom middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Then decorate endpoints:
@app.post("/v1/chat/completions")
@limiter.limit("100/minute")
async def chat_completion(...):
    ...
```

---

## 5. Steps Taken

1. **Read api_server.py** → Identified authentication bypass, CORS misconfiguration, credential logging
2. **Analyzed InferenceConfig class** → Found hardcoded default API key and missing validation
3. **Examined endpoint handlers** → Confirmed no auth checks on `/v1/chat/completions` or `/v1/embeddings`
4. **Read model_loader.py** → Discovered `trust_remote_code=True` security risk
5. **Reviewed prompt_builder.py** → Found input validation gaps (no max length enforcement before truncation)
6. **Checked resource management** → Identified httpx client leak (no shutdown handler)
7. **Analyzed concurrency patterns** → Found non-thread-safe request counter

**Self-Correction**: Initially I thought the API key was being used since it's defined in config. Upon closer inspection, the key is never actually validated anywhere—it's only logged at startup. This is a classic case of "security theater" (having the appearance of auth without enforcement).

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual code review | Line-by-line security analysis |
| Pattern matching | Identified hardcoded credentials, CORS wildcards, missing auth |
| OWASP Top 10 checklist | Systematic vulnerability scanning |

---

## 7. Verification

### Verify Authentication is Enforced

```bash
# Before fix - should fail after fix:
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'
# Expected: 401 Unauthorized (after fix)
```

### Verify CORS is Restricted

```bash
# Check CORS headers in response:
curl -I -X OPTIONS http://localhost:8000/v1/chat/completions \
  -H "Origin: https://evil.com"
# Expected: No Access-Control-Allow-Origin: * (after fix)
```

### Verify Credentials Not Logged

```bash
# Check logs for API key exposure:
grep -r "sk-guwen" /var/log/
# Expected: No matches (after fix)
```

### Verify httpx Client Cleanup

```python
# Add test for shutdown handler:
import asyncio
from src.inference.api_server import create_app

app = create_app()
async def test_shutdown():
    await app.router.startup()
    await app.router.shutdown()
    # Verify client.closed is True
```

---

## Summary

| Category | Count |
|----------|-------|
| 🔴 Blocker | 3 |
| 🟡 Suggestion | 5 |
| ⚪ Nit | 1 |
| **Hidden Issues** | 7 |
| **Total** | **15** |

### Priority Order for Production Deployment

1. **Implement API key authentication** (Fix #1) - Critical for production
2. **Remove credential logging** (Fix #3) - Prevents secret leakage
3. **Restrict CORS** (Fix #2) - Blocks cross-origin attacks
4. **Add request size limits** (Fix #6) - Prevents DoS
5. **Add shutdown handler** (Fix #7) - Prevents resource leaks
6. **Review trust_remote_code** (Fix #5) - Depends on model source trustworthiness

---

```
📋 交付确认
□ 目标匹配: 安全审计 → 15项发现（含8项超出提问的隐患）
□ 边界覆盖: 认证/授权/CORS/日志/资源管理/输入验证/并发安全
□ 风险可控: 3项Blocker需修复后方可上线，附验证命令
```
