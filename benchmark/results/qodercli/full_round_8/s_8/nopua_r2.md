# Scenario 8: Inference Config Security Audit
## Condition: nopua | Run: 2
## Duration: 154.49s

---

## Security Audit Report: Inference Module

### Executive Summary

The inference module at `src/inference/` has **6 critical/high security issues** that must be addressed before production deployment. The most severe issues are: API key exposure in logs, missing authentication middleware, hardcoded credentials, and CORS misconfiguration.

---

## 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **API Key Logged in Plaintext** | CRITICAL | `api_server.py:130` |
| 2 | **No Authentication Middleware** | CRITICAL | `api_server.py:155-224` |
| 3 | **Hardcoded Default API Key** | HIGH | `api_server.py:51`, `inference_config.yaml:16` |
| 4 | **CORS Misconfiguration (Allow All Origins + Credentials)** | HIGH | `api_server.py:122-128` |
| 5 | **HTTP Client Never Closed (Resource Leak)** | MEDIUM | `api_server.py:135` |
| 6 | **Silent Exception Handling in Streaming** | MEDIUM | `api_server.py:319-320` |

---

## 2. Hidden Issues Discovered

| # | Hidden Issue | Category | Location |
|---|--------------|----------|----------|
| A | **vLLM Backend Uses HTTP Without TLS** | Network Security | `api_server.py:44`, `inference_config.yaml:7` |
| B | **`trust_remote_code: true` Without Code Review** | Supply Chain Risk | `model_loader.py:28`, `inference_config.yaml:29` |
| C | **Test Validates Insecure Behavior** | Test Quality | `test_api_server.py:32-50` |
| D | **Docker Compose Exposes Default API Key** | Configuration | `docker-compose.yml:57` |
| E | **Config Comment Acknowledges But Doesn't Fix Logging** | Documentation Risk | `inference_config.yaml:15-16` |
| F | **Unused Import (`datetime`)** | Code Quality | `api_server.py:22` |
| G | **HTTPX Client Created Without Shutdown Handler** | Resource Management | `api_server.py:135` |

---

## 3. Root Cause

### Primary Root Causes

1. **Security as Afterthought**: The code was designed for functionality first, with security bolted on incompletely:
   - An `api_key` config exists but is never validated on incoming requests
   - CORS allows all origins with credentials enabled (dangerous combination)
   - API key is logged at startup despite being "secret"

2. **Hardcoded Credentials Pattern**: Multiple locations hardcode or default to known values:
   - `api_server.py:51`: Falls back to `"sk-guwen-default-key-2024"` if env var missing
   - `inference_config.yaml:16`: Contains plaintext API key in version control
   - `docker-compose.yml:57`: Ships with default key in environment

3. **Missing Defense in Depth**: No layered security:
   - No rate limiting
   - No request validation beyond pydantic schema
   - No backend health checks before proxying
   - No audit logging of failed auth attempts

### Secondary Causes

4. **Resource Management Gaps**: httpx.AsyncClient created without lifecycle management:
   - No shutdown handler to close the client
   - Could lead to connection pool exhaustion under load

5. **Error Handling Anti-Patterns**: Silent exception swallowing in streaming:
   - JSON parse errors silently skipped (`continue` statement)
   - Makes debugging production issues difficult

---

## 4. Recommended Fix

### Fix 1: Remove API Key Logging (CRITICAL)

**File: `api_server.py:130-131`**

```python
# BEFORE (line 130):
logger.info(f"Server starting with API key: {config.api_key}")
logger.info(f"vLLM backend: {config.vllm_url}")

# AFTER:
logger.info(f"Guwen-LLM API server starting on {config.host}:{config.port}")
logger.info(f"vLLM backend configured: {config.vllm_url}")
# Note: Never log API keys or secrets
```

---

### Fix 2: Add Authentication Middleware (CRITICAL)

**File: `api_server.py`** - Add after imports:

```python
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    config: InferenceConfig = None,
) -> str:
    """Verify API key from Authorization header."""
    if not creds:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    expected_key = config.api_key if config else app.state.config.api_key
    if creds.credentials != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return creds.credentials
```

**File: `api_server.py:155`** - Update route:

```python
@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key),  # Add auth dependency
):
    """Handle chat completion requests."""
    # ... rest unchanged
```

Apply same pattern to `/v1/embeddings` endpoint.

---

### Fix 3: Remove Hardcoded Default Key (HIGH)

**File: `api_server.py:51`**

```python
# BEFORE:
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# AFTER:
api_key: str = os.environ.get("GUWEN_API_KEY")

def __post_init__(self):
    if not self.api_key:
        raise ValueError(
            "GUWEN_API_KEY environment variable must be set. "
            "Generate a secure key with: openssl rand -hex 16"
        )
```

**File: `inference_config.yaml:16`** - Remove or comment out:

```yaml
# BEFORE:
api_key: "sk-guwen-default-key-2024"

# AFTER:
# api_key: Set via GUWEN_API_KEY environment variable (required)
# Generate secure key: openssl rand -hex 16
```

---

### Fix 4: Fix CORS Configuration (HIGH)

**File: `api_server.py:122-128`**

```python
# BEFORE:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # DANGEROUS with wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# AFTER:
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicit list only
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],  # Restrict to needed methods
    allow_headers=["Authorization", "Content-Type"],  # Only needed headers
    max_age=600,  # Cache preflight for 10 minutes
)
```

---

### Fix 5: Add HTTP Client Lifecycle Management (MEDIUM)

**File: `api_server.py:135-137`** - Add shutdown handler:

```python
# Store config in app state
app.state.config = config
app.state.http_client = httpx.AsyncClient(timeout=config.timeout)
app.state.request_count = 0

# Add shutdown handler
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()
```

---

### Fix 6: Improve Streaming Error Handling (MEDIUM)

**File: `api_server.py:319-320`**

```python
# BEFORE:
except (json.JSONDecodeError, KeyError, IndexError):
    continue

# AFTER:
except (json.JSONDecodeError, KeyError, IndexError) as e:
    logger.warning(f"Failed to parse streaming chunk: {e}")
    error_chunk = {
        "error": {"message": f"Stream parse error: {str(e)}", "type": "parse_error"},
    }
    yield f"data: {json.dumps(error_chunk)}\n\n"
```

---

### Fix 7: Additional Recommendations

#### 7A: Add Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Then decorate endpoints:
@app.post("/v1/chat/completions")
@limiter.limit("100/minute")
async def chat_completion(...):
    ...
```

#### 7B: Use HTTPS for vLLM Backend

Change `vllm_url` from `http://localhost:8001` to `https://localhost:8001` and configure SSL certificates.

#### 7C: Review `trust_remote_code` Setting

Set `trust_remote_code: false` unless you have audited the remote code from the model repository.

---

## 5. Steps Taken

1. **Read all source files** in `src/inference/`:
   - `api_server.py` (364 lines) - Full analysis
   - `model_loader.py` (122 lines) - Full analysis
   - `prompt_builder.py` (171 lines) - Full analysis

2. **Searched for sensitive patterns**:
   - API key usage across codebase
   - Environment variable handling
   - Credential storage patterns

3. **Analyzed configuration files**:
   - `configs/inference_config.yaml` - Found hardcoded API key
   - `docker-compose.yml` - Found default key in environment

4. **Reviewed test files**:
   - `tests/test_api_server.py` - Found test validating no-auth behavior

5. **Identified security anti-patterns**:
   - Secret logging
   - Missing auth middleware
   - CORS wildcard + credentials
   - Resource leaks

6. **Cross-referenced with deployment config**:
   - Docker compose environment variables
   - Config file comments acknowledging issues

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all source files line-by-line |
| `Grep` | Search for API key patterns, logging calls, exception handlers |
| `Glob` | Find all files in inference module and configs |
| Manual Analysis | Security pattern recognition, vulnerability identification |

---

## 7. Verification

### Immediate Verification Commands

```bash
# 1. Verify API key is NOT logged after fix:
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -c "
from src.inference.api_server import create_app, InferenceConfig
import logging
logging.basicConfig(level=logging.INFO)
config = InferenceConfig(api_key='sk-test-secret-key')
app = create_app(config)
print('Check logs above - should NOT contain API key')
" 2>&1 | grep -i "api.key\|secret\|sk-"
# Expected: No output (no secrets in logs)
```

```bash
# 2. Verify authentication is required:
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"guwen-llm-7b-chat","messages":[{"role":"user","content":"hello"}]}'
# Expected: 401 Unauthorized (missing auth header)

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong-key" \
  -d '{"model":"guwen-llm-7b-chat","messages":[{"role":"user","content":"hello"}]}'
# Expected: 403 Forbidden (invalid key)
```

```bash
# 3. Verify CORS is restricted:
curl -X OPTIONS http://localhost:8000/v1/chat/completions \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -i | grep -i "access-control"
# Expected: No ACAO header or specific origin (not *)
```

```bash
# 4. Verify no hardcoded default key:
python -c "
from src.inference.api_server import InferenceConfig
import os
os.environ.pop('GUWEN_API_KEY', None)
try:
    config = InferenceConfig()
    print('ERROR: Should have raised ValueError')
except ValueError as e:
    print(f'CORRECT: {e}')
"
```

### Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] API key is NOT present in any logs (startup, request, error)
- [ ] All `/v1/*` endpoints require valid `Authorization: Bearer <key>` header
- [ ] CORS `allow_origins` is an explicit list (not `["*"]`)
- [ ] `GUWEN_API_KEY` environment variable is set with cryptographically secure value
- [ ] No API keys committed to version control (`.env`, `*.yaml`, `*.yml`)
- [ ] HTTP client is properly closed on shutdown
- [ ] vLLM backend uses HTTPS in production
- [ ] Rate limiting is enabled to prevent abuse
- [ ] `trust_remote_code: false` unless explicitly audited

---

## Summary

**Do not deploy to production until Issues #1-4 are fixed.** These are critical security vulnerabilities that would expose your API to unauthorized access, credential theft, and potential abuse.

The fixes are straightforward and can be implemented in a single commit. I recommend creating a security-focused PR that addresses all items in Section 4, then running the verification commands in Section 7 before merging.
