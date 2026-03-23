# Scenario 8: Inference Config Security Audit
## Condition: nopua | Run: 1
## Duration: 38.87s

---

Based on my thorough analysis of the provided source files, here is the **Security Audit Report**:

---

## 🔒 Security Audit Report: Inference Module

### 1. Issues Found

| ID | Severity | Location | Issue |
|----|----------|----------|-------|
| **SEC-001** | 🔴 **CRITICAL** | `api_server.py:46` | **Hardcoded API Key with Weak Default** - Default API key `sk-guwen-default-key-2024` is committed in code and logged at startup |
| **SEC-002** | 🔴 **CRITICAL** | `api_server.py:75` | **Wildcard CORS Policy** - `allow_origins=["*"]` with `allow_credentials=True` enables credential theft from any origin |
| **SEC-003** | 🟠 **HIGH** | `api_server.py:46` | **API Key Logged to Console** - `logger.info(f"Server starting with API key: {config.api_key}")` exposes secrets in logs |
| **SEC-004** | 🟠 **HIGH** | `api_server.py:129-138` | **No Authentication Enforcement** - `/v1/chat/completions` endpoint does not validate the API key |
| **SEC-005** | 🟠 **HIGH** | `model_loader.py:25` | **`trust_remote_code=True`** - Allows arbitrary code execution from model repository |
| **SEC-006** | 🟡 **MEDIUM** | `api_server.py:169-176` | **Unvalidated Proxy to vLLM** - No input sanitization before proxying requests; potential SSRF via `vllm_url` config |
| **SEC-007** | 🟡 **MEDIUM** | `api_server.py:46` | **Weak Environment Variable Fallback** - `GUWEN_API_KEY` defaults to hardcoded value instead of failing secure |
| **SEC-008** | 🟡 **MEDIUM** | `prompt_builder.py:103-105` | **Prompt Injection Vulnerability** - User input directly concatenated into ChatML format without sanitization |
| **SEC-009** | 🟢 **LOW** | `api_server.py:46` | **Sensitive Data in Dataclass** - API key stored in plain dataclass with no protection |

---

### 2. Hidden Issues (Beyond the Ask)

| ID | Issue | Impact |
|----|-------|--------|
| **HIDDEN-001** | **No Rate Limiting** - No request throttling; vulnerable to DoS attacks | Service availability |
| **HIDDEN-002** | **No Request Size Limits** - `max_prompt_length` only truncates, doesn't reject oversized payloads | Memory exhaustion |
| **HIDDEN-003** | **No Input Validation on `user` Field** - `ChatCompletionRequest.user` accepts arbitrary strings without validation | Logging injection / IDOR |
| **HIDDEN-004** | **No HTTPS Enforcement** - Server binds to `0.0.0.0` with no TLS configuration | Man-in-the-middle attacks |
| **HIDDEN-005** | **No Health Check Authentication** - `/health` endpoint exposes internal state (request count, backend URL) to unauthenticated users | Information disclosure |
| **HIDDEN-006** | **Embeddings Endpoint Unprotected** - `/v1/embeddings` proxies without auth; could be abused for free inference | Resource abuse |
| **HIDDEN-007** | **No Audit Logging** - No request/response logging for security monitoring | Incident response blind spot |
| **HIDDEN-008** | **Stream Endpoint Error Leakage** - `_stream_completion` yields error details to client (`error_chunk`) | Information disclosure |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Security as Afterthought** - The module was designed for functionality, not production security. Authentication exists as a config field but is never enforced.

2. **Insecure Defaults** - Every security-sensitive setting defaults to the insecure option:
   - CORS: `["*"]` with credentials
   - API key: hardcoded fallback
   - Model loading: `trust_remote_code=True`

3. **Trust Boundary Violations** - The code trusts:
   - User input (no sanitization before prompt construction)
   - Configuration values (no validation of `vllm_url`)
   - External model repositories (remote code execution enabled)

4. **Logging Anti-Patterns** - Sensitive data (API keys) logged at INFO level violates security best practices.

---

### 4. Recommended Fixes

#### P0 (Before Production)

```python
# api_server.py - Fix SEC-001, SEC-003, SEC-007
@dataclass
class InferenceConfig:
    # ... other fields ...
    
    # FAIL SECURE: No default, require env var or explicit config
    api_key: str = field(
        default_factory=lambda: os.environ.get("GUWEN_API_KEY") or _require_api_key()
    )

def _require_api_key() -> str:
    raise ValueError("GUWEN_API_KEY environment variable must be set for production")

# Remove the logging of API key (SEC-003)
logger.info("Server starting - API key configured")  # Don't log the actual key
```

```python
# api_server.py - Fix SEC-002
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-domain.com"],  # Explicit whitelist
    allow_credentials=False,  # Disable unless absolutely necessary
    allow_methods=["POST", "GET"],  # Restrict to needed methods
    allow_headers=["Authorization", "Content-Type"],
)
```

```python
# api_server.py - Fix SEC-004: Add authentication middleware
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != app.state.config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest, 
                          api_key: str = Depends(verify_api_key)):
    # ... existing logic ...
```

```python
# model_loader.py - Fix SEC-005
@dataclass
class ModelConfig:
    # ... other fields ...
    trust_remote_code: bool = False  # Default to False; enable only with verified models
    
    # Add hash verification for model integrity
    expected_model_hash: Optional[str] = None
```

#### P1 (Before Scale)

```python
# api_server.py - Fix HIDDEN-001: Add rate limiting
from slowapi import SlowAPILimiter, _rate_limit_exceeded_handler

app.state.limiter = SlowAPILimiter()
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/chat/completions")
@limiter.limit("10/minute")  # Adjust based on capacity
async def chat_completion(...):
    # ...
```

```python
# api_server.py - Fix HIDDEN-002: Add request size limits
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Restrict in production

# Add max body size
app.config.max_body_size = 10 * 1024 * 1024  # 10MB limit
```

```python
# prompt_builder.py - Fix SEC-008: Sanitize user input
def _sanitize_for_chatml(self, text: str) -> str:
    """Remove or escape ChatML special tokens from user input."""
    # Prevent prompt injection by stripping special tokens
    text = re.sub(r'
