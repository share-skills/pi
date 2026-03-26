# Scenario 8: Inference Config Security Audit
## Condition: nopua | Run: 1
## Duration: 45.45s

---

Based on my thorough analysis of the provided inference module source code, I've identified multiple security issues. Let me document them systematically:

---

## 🔒 Security Audit Report — Inference Module

### 1. Issues Found

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | **CRITICAL** | Hardcoded API key with weak default | `api_server.py:36` |
| 2 | **CRITICAL** | No API key validation on endpoints | `api_server.py:94-107` |
| 3 | **HIGH** | Overly permissive CORS policy | `api_server.py:66-71` |
| 4 | **HIGH** | SSRF vulnerability via vLLM URL | `api_server.py:34, 125-138` |
| 5 | **MEDIUM** | Default system prompt could enable prompt injection | `api_server.py:37, 200-212` |
| 6 | **MEDIUM** | No rate limiting or DoS protection | `api_server.py:global` |
| 7 | **MEDIUM** | Sensitive data logged (API key) | `api_server.py:76` |
| 8 | **LOW** | `trust_remote_code=True` enables arbitrary code execution | `model_loader.py:28` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Why It's Hidden | Risk |
|---|-------|-----------------|------|
| H1 | **No input validation on user messages** | ChatMessage model only validates role/content types, not content length or malicious patterns | Prompt injection, memory exhaustion |
| H2 | **Unbounded request parameters** | `max_tokens`, `n`, `temperature` have no server-side enforcement beyond defaults | Resource exhaustion, cost attacks |
| H3 | **Missing authentication on `/v1/models` and `/health`** | These endpoints leak internal configuration without auth | Information disclosure |
| H4 | **httpx client reused without connection pool limits** | Single AsyncClient shared across all requests | Connection exhaustion, potential cross-request data leakage |
| H5 | **No request ID or audit logging** | Request count tracked but no structured logging | Cannot trace attacks or debug incidents |
| H6 | **Streaming endpoint yields unvalidated chunks** | `_stream_completion` passes backend data directly | Could proxy malicious content from compromised backend |
| H7 | **Embedding endpoint accepts arbitrary JSON** | No schema validation on `/v1/embeddings` body | Potential deserialization attacks |

---

### 3. Root Causes

1. **Development-first mindset**: Code written for local development, not production deployment
2. **No security threat modeling**: Authentication, authorization, and input validation were not designed into the architecture
3. **Implicit trust boundaries**: Assumes backend (vLLM) is trusted and network is secure
4. **Defaults optimized for convenience, not security**: Weak API key, open CORS, permissive settings

---

### 4. Recommended Fixes

#### Critical (Must Fix Before Production)

```python
# Fix 1: Remove hardcoded API key, require environment variable
# api_server.py:36
api_key: str = os.environ.get("GUWEN_API_KEY")
if not self.api_key:
    raise ValueError("GUWEN_API_KEY environment variable must be set")

# Fix 2: Add API key validation middleware
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Apply to all routes:
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])

# Fix 3: Restrict CORS to known origins
# api_server.py:66-71
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Explicit list
    allow_credentials=False,  # Unless absolutely needed
    allow_methods=["POST", "GET"],  # Only required methods
    allow_headers=["Authorization", "Content-Type"],
)

# Fix 4: Validate vLLM URL is internal/safe
import ipaddress
from urllib.parse import urlparse

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not ip.is_private and not ip.is_loopback
    except ValueError:
        # DNS hostname - validate against allowlist
        allowed_hosts = ["localhost", "127.0.0.1", "vllm.internal"]
        return parsed.hostname in allowed_hosts
```

#### High Priority

```python
# Fix 5: Don't log sensitive data
# api_server.py:76
logger.info(f"Server starting")  # Removed API key from log
logger.info(f"vLLM backend configured")

# Fix 6: Add rate limiting
from slowapi import SlowRateLimiter
from slowapi.errors import RateLimitExceeded

limiter = SlowRateLimiter(key_func=lambda request: request.client.host)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, ...)

# Apply per-endpoint:
@limiter.limit("100/minute")
@app.post("/v1/chat/completions")

# Fix 7: Add input validation
class ChatMessage(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1, max_length=100000)  # Reasonable limit

class ChatCompletionRequest(BaseModel):
    # Add max constraints
    max_tokens: Optional[int] = Field(default=2048, le=8192, ge=1)
    n: Optional[int] = Field(default=1, le=5, ge=1)
    temperature: Optional[float] = Field(default=0.7, le=2.0, ge=0.0)
```

#### Medium Priority

```python
# Fix 8: Set trust_remote_code based on config, default False
# model_loader.py:28
trust_remote_code: bool = False  # Only enable for verified models

# Fix 9: Add health endpoint authentication
@app.get("/health")
async def health_check(api_key: str = Depends(verify_api_key)):
    ...

# Fix 10: Add request timeout and connection limits
app.state.http_client = httpx.AsyncClient(
    timeout=config.timeout,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
)
```

---

### 5. Steps Taken

1. **Read all 4 source files** line by line, focusing on:
   - Configuration handling
   - Input validation
   - Authentication/authorization
   - External integrations
   - Error handling

2. **Analyzed data flow**:
   - User input → validation → processing → backend → response
   - Configuration loading and usage
   - Credential storage and transmission

3. **Identified trust boundaries**:
   - Client ↔ API server (no auth)
   - API server ↔ vLLM backend (implicit trust)
   - Environment ↔ application (assumed safe)

4. **Reviewed security-relevant patterns**:
   - CORS configuration
   - Logging statements
   - Model loading settings
   - Streaming response handling

---

### 6. Tools Used

- Manual code review (static analysis)
- OWASP Top 10 mental checklist
- FastAPI security best practices reference
- Python security pattern recognition

---

### 7. Verification

**I have verified findings by:**

| Finding | Verification Method |
|---------|--------------------|
| Hardcoded API key | ✅ Confirmed at line 36: `api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")` |
| No API validation | ✅ Confirmed: No `Depends()` or auth checks on any route |
| Open CORS | ✅ Confirmed line 68: `allow_origins=["*"]` |
| API key in logs | ✅ Confirmed line 76: `logger.info(f"Server starting with API key: {config.api_key}")` |
| trust_remote_code | ✅ Confirmed model_loader.py:28: `trust_remote_code: bool = True` |
| SSRF risk | ✅ Confirmed: vLLM URL used directly at line 125 without validation |

---

## Summary

**This code is NOT production-ready.** It was clearly written for local development/testing and lacks fundamental security controls:

1. **Authentication**: Effectively non-existent (weak default key, never validated)
2. **Input validation**: Minimal to none
3. **Network security**: Open CORS, potential SSRF
4. **Observability**: Logs secrets, no audit trail
5. **Resource protection**: No rate limiting, unbounded parameters

**Recommendation**: Do not deploy to production until Critical and High priority issues are addressed. At minimum:
- Require strong API key via environment variable
- Add authentication middleware to all endpoints
- Restrict CORS to specific origins
- Remove sensitive data from logs
- Validate/sanitize all inputs
