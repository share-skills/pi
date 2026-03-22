# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 76.04s

---

Now I have completed my investigation. Let me compile the comprehensive security audit report:

---

# 🔒 Inference Module Security Audit Report

## 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Hardcoded API key with default fallback** | `api_server.py:51` | 🔴 Critical |
| 2 | **API key logged in plaintext** | `api_server.py:122` | 🔴 Critical |
| 3 | **Overly permissive CORS policy** | `api_server.py:116-119` | 🟠 High |
| 4 | **No API key authentication enforcement** | `api_server.py:147-205` | 🟠 High |
| 5 | **trust_remote_code=True by default** | `model_loader.py:28` | 🟠 High |
| 6 | **HTTP backend without TLS** | `api_server.py:44` | 🟠 High |
| 7 | **Race condition in request counter** | `api_server.py:154` | 🟡 Medium |
| 8 | **Missing input validation on user messages** | `api_server.py:235-253` | 🟡 Medium |
| 9 | **Unused import (re, Tuple, field)** | `prompt_builder.py:12-15` | 🟢 Low |
| 10 | **Resource leak: httpx client never closed** | `api_server.py:127` | 🟡 Medium |

---

## 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 1 | **Config file contains hardcoded API key** | `configs/inference_config.yaml:16` | Secrets Management |
| 2 | **Config vllm_url hardcoded without TLS** | `configs/inference_config.yaml:7` | Network Security |
| 3 | **Exception details exposed to clients** | `api_server.py:228` | Information Disclosure |
| 4 | **No rate limiting on endpoints** | `api_server.py:132-229` | DoS Vulnerability |
| 5 | **No request size limits** | `api_server.py:67-79` | DoS/Resource Exhaustion |
| 6 | **Silent exception swallowing in stream handler** | `api_server.py:300-301` | Error Handling |
| 7 | **GPU memory not properly released on error** | `model_loader.py:115-119` | Resource Management |
| 8 | **No timeout on streaming responses** | `api_server.py:256-307` | Resource Exhaustion |
| 9 | **Prompt injection vulnerability via user content** | `prompt_builder.py:118-126` | Prompt Security |
| 10 | **No validation of message role values** | `api_server.py:61-64` | Input Validation |

---

## 3. Root Cause

### 3.1 Authentication & Secrets (Issues 1, 2, 4, Config 1)
**Root Cause:** The API key system is fundamentally broken:
- Line 51: `api_key` has a hardcoded default value that will be used if `GUWEN_API_KEY` env var is not set
- Line 122: The API key is logged at startup, exposing it in logs
- Lines 147-205: The `/v1/chat/completions` endpoint does NOT verify the API key from requests

```python
# api_server.py:51
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")  # ❌ Default key

# api_server.py:122
logger.info(f"Server starting with API key: {config.api_key}")  # ❌ Leaked in logs

# api_server.py:147-205 - No auth check anywhere in chat_completion()
```

### 3.2 CORS Misconfiguration (Issue 3)
**Root Cause:** Wildcard CORS allows any origin to make requests:
```python
# api_server.py:114-119
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Allows any website to make requests
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3.3 Remote Code Execution Risk (Issue 5)
**Root Cause:** `trust_remote_code=True` allows arbitrary code execution from model files:
```python
# model_loader.py:28
trust_remote_code: bool = True  # ❌ Executes untrusted code from model repo
```

### 3.4 Insecure Transport (Issue 6, Config 2)
**Root Cause:** Backend communication uses plaintext HTTP:
```python
# api_server.py:44
vllm_url: str = "http://localhost:8001"  # ❌ No encryption
```

### 3.5 Race Condition (Issue 7)
**RootCause:** Non-atomic increment of shared counter:
```python
# api_server.py:154
app.state.request_count += 1  # ❌ Not thread-safe
```

### 3.6 Resource Leak (Issue 10)
**Root Cause:** httpx.AsyncClient created but never closed:
```python
# api_server.py:127
app.state.http_client = httpx.AsyncClient(timeout=config.timeout)  # ❌ No cleanup
```

---

## 4. Recommended Fix

### 4.1 API Key Authentication (Critical)

```python
# BEFORE (api_server.py:51)
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# AFTER
api_key: str = os.environ.get("GUWEN_API_KEY")
if not self.api_key:
    raise ValueError("GUWEN_API_KEY environment variable must be set")
```

```python
# ADD authentication middleware (after line 119)
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    if creds is None or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials

# ADD to all protected routes (example for chat_completion)
@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    _: str = Depends(verify_api_key)  # Add auth dependency
):
    # ... existing code
```

### 4.2 Remove API Key Logging

```python
# BEFORE (api_server.py:122)
logger.info(f"Server starting with API key: {config.api_key}")

# AFTER
logger.info("Server starting with API key authentication enabled")
```

### 4.3 Restrict CORS

```python
# BEFORE (api_server.py:116-119)
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],

# AFTER
allow_origins=["https://your-trusted-domain.com"],  # Explicit origins
allow_credentials=True,
allow_methods=["POST", "GET"],  # Limit methods
allow_headers=["Authorization", "Content-Type"],  # Limit headers
```

### 4.4 Disable trust_remote_code

```python
# BEFORE (model_loader.py:28)
trust_remote_code: bool = True

# AFTER
trust_remote_code: bool = False  # Only load models with local code
```

### 4.5 Enable TLS for Backend

```python
# BEFORE (api_server.py:44)
vllm_url: str = "http://localhost:8001"

# AFTER
vllm_url: str = os.environ.get("VLLM_URL", "https://localhost:8001")
```

### 4.6 Fix Race Condition

```python
# BEFORE (api_server.py:128)
app.state.request_count = 0

# AFTER - Use asyncio lock or atomic counter
import asyncio
app.state.request_lock = asyncio.Lock()
app.state.request_count = 0

# In chat_completion (line 154)
async with app.state.request_lock:
    app.state.request_count += 1
```

### 4.7 Close httpx Client

```python
# ADD shutdown handler (after line 230)
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()
```

### 4.8 Add Input Validation

```python
# ADD to ChatMessage class (api_server.py:61-64)
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ('system', 'user', 'assistant'):
            raise ValueError('role must be system, user, or assistant')
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if len(v) > 100000:  # Reasonable limit
            raise ValueError('content too long')
        return v
```

---

## 5. Steps Taken

1. **Read all 4 source files** in `nopua/benchmark/test-project/src/inference/` directory
2. **Searched for security-sensitive patterns**: api_key, secret, password, token, CORS, trust_remote_code, yaml.load
3. **Analyzed data flow**: Traced request handling from endpoint → vLLM backend → response
4. **Reviewed configuration file**: Read `configs/inference_config.yaml` to identify hardcoded secrets
5. **Cross-referenced findings**: Compared code against OWASP Top 10 and API security best practices
6. **Verified each issue**: Located exact line numbers and documented evidence
7. **Identified hidden issues**: Extended search beyond surface-level bugs to find related vulnerabilities

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 4 Python source files + config YAML |
| `Grep` | Search for security patterns (api_key, CORS, trust_remote_code, exceptions) |
| `Glob` | Find configuration files (inference_config.yaml, .env files) |
| `Bash` | List directory contents to verify file structure |

---

## 7. Verification

### Verification Commands

```bash
# 1. Verify no hardcoded API keys in source
grep -n "sk-guwen-default" nopua/benchmark/test-project/src/inference/*.py
# Expected: Should find the issue at api_server.py:51

# 2. Verify CORS configuration
grep -A4 "CORSMiddleware" nopua/benchmark/test-project/src/inference/api_server.py
# Expected: Shows allow_origins=["*"]

# 3. Verify trust_remote_code setting
grep -n "trust_remote_code" nopua/benchmark/test-project/src/inference/model_loader.py
# Expected: Shows True at line 28

# 4. Verify API key logging
grep -n "api_key" nopua/benchmark/test-project/src/inference/api_server.py | grep logger
# Expected: Shows line 122 logging the key

# 5. Check config file for hardcoded secrets
grep -n "api_key" nopua/benchmark/test-project/configs/inference_config.yaml
# Expected: Shows hardcoded key at line 16

# 6. Verify missing auth on endpoints
grep -B2 -A20 "def chat_completion" nopua/benchmark/test-project/src/inference/api_server.py
# Expected: No authentication check found
```

### Verification Evidence

```
$ grep -n "sk-guwen-default" nopua/benchmark/test-project/src/inference/*.py
nopua/benchmark/test-project/src/inference/api_server.py:51:    api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

$ grep -A4 "CORSMiddleware" nopua/benchmark/test-project/src/inference/api_server.py
from fastapi.middleware.cors import CORSMiddleware
--
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],

$ grep -n "trust_remote_code" nopua/benchmark/test-project/src/inference/model_loader.py
28:    trust_remote_code: bool = True
77:                trust_remote_code=self.config.trust_remote_code,

$ grep -n "api_key.*logger\|logger.*api_key" nopua/benchmark/test-project/src/inference/api_server.py
122:    logger.info(f"Server starting with API key: {config.api_key}")
```

---

## Summary

| Category | Count |
|----------|-------|
| **Critical** | 2 |
| **High** | 5 |
| **Medium** | 4 |
| **Low** | 1 |
| **Total Surface Issues** | 10 |
| **Hidden Issues** | 10 |

**⚠️ Regression Risk:** This module is NOT production-ready. The authentication system is completely non-functional (API key is defined but never checked), and multiple high-severity issues exist that could lead to unauthorized access, data leakage, or remote code execution.
