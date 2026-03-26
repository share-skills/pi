# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 133.14s

---

Now I have completed the investigation. Let me provide the structured security audit report:

---

# Security Audit Report: Inference Module

## 1. Issues Found

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | 🔴 Blocker | `api_server.py:51` | Hardcoded default API key with fallback |
| 2 | 🔴 Blocker | `api_server.py:117-120` | Overly permissive CORS policy (allow all origins/methods/headers) |
| 3 | 🔴 Blocker | `api_server.py:123` | API key logged in plain text |
| 4 | 🟡 Critical | `model_loader.py:28` | `trust_remote_code=True` enables arbitrary code execution |
| 5 | 🟡 Critical | `api_server.py:44` | Hardcoded backend URL (no configuration validation) |
| 6 | 🟡 Critical | `api_server.py:148-217` | No authentication enforcement on `/v1/chat/completions` endpoint |
| 7 | 🟡 Major | `api_server.py:128` | HTTP client created without connection pooling limits |
| 8 | 🟡 Major | `api_server.py:155` | Thread-unsafe request counter increment |
| 9 | 🟡 Major | `prompt_builder.py:100` | Unvalidated template injection via `text` parameter |
| 10 | 🟡 Major | `api_server.py:322-331` | Config file loaded without path validation (path traversal risk) |
| 11 | ⚪ Minor | `api_server.py:229-240` | `/v1/embeddings` endpoint exposes raw backend errors |
| 12 | ⚪ Minor | `model_loader.py:107-121` | Model unload relies on `del` without guaranteed cleanup |

---

## 2. Hidden Issues

| # | Category | Location | Issue |
|---|----------|----------|-------|
| H1 | Security | `api_server.py:51` | Default API key `"sk-guwen-default-key-2024"` is predictable and documented in source |
| H2 | Security | `api_server.py:148-217` | Prompt injection vector: user messages directly concatenated without sanitization |
| H3 | Performance | `api_server.py:128` | Single shared httpx client across all requests - potential connection exhaustion |
| H4 | Correctness | `api_server.py:155` | Race condition: `app.state.request_count += 1` not atomic in async context |
| H5 | Correctness | `prompt_builder.py:152-160` | Character-based truncation may split multi-byte Unicode mid-character |
| H6 | Resource | `api_server.py:128` | No lifecycle management for httpx client (no close on shutdown) |
| H7 | Configuration | `model_loader.py:25` | `gpu_memory_utilization=0.9` hardcoded - may cause OOM on memory-constrained GPUs |
| H8 | Observability | `api_server.py:184` | Error logging loses exception stack trace (only logs message) |

---

## 3. Root Cause

### Primary Root Causes

**RC1 - Insecure Defaults** (`api_server.py:51`, `model_loader.py:28`)
- API key defaults to a known value if `GUWEN_API_KEY` env var is not set
- `trust_remote_code=True` allows model authors to execute arbitrary Python code

**RC2 - Missing Security Controls** (`api_server.py:117-120`, `148-217`)
- CORS policy permits any origin, method, and header
- No authentication middleware or API key validation on protected endpoints
- User input flows directly into prompt templates without sanitization

**RC3 - Unsafe Concurrency Patterns** (`api_server.py:155`)
- Async request counter increment is not thread-safe
- FastAPI/Uvicorn runs multiple workers; shared state requires synchronization

**RC4 - Information Leakage** (`api_server.py:123`, `240`)
- Sensitive credentials logged at INFO level
- Backend error details exposed to clients without sanitization

---

## 4. Recommended Fix

### Fix 1: Secure API Key Handling
```python
# api_server.py:51
# Before:
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# After:
api_key: str = os.environ.get("GUWEN_API_KEY")
if not api_key:
    raise ValueError("GUWEN_API_KEY environment variable must be set")
```

### Fix 2: Restrict CORS Policy
```python
# api_server.py:115-121
# Before:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# After:
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Fix 3: Add Authentication Middleware
```python
# api_server.py: Add after line 130
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(
    creds: HTTPAuthorizationCredentials = Security(security)
) -> str:
    if creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials

# Then protect routes:
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completion(request: ChatCompletionRequest):
    ...
```

### Fix 4: Disable trust_remote_code by Default
```python
# model_loader.py:28
# Before:
trust_remote_code: bool = True

# After:
trust_remote_code: bool = False  # Only enable for verified models
```

### Fix 5: Fix Thread-Safe Counter
```python
# api_server.py: Add import and use atomic counter
import asyncio

# In create_app(), line 129:
app.state.request_count = 0
app.state._count_lock = asyncio.Lock()

# Line 155:
async with app.state._count_lock:
    app.state.request_count += 1
```

### Fix 6: Remove Credential Logging
```python
# api_server.py:123
# Before:
logger.info(f"Server starting with API key: {config.api_key}")

# After:
logger.info("Server starting with API key: [REDACTED]")
logger.info(f"vLLM backend: {config.vllm_url}")
```

### Fix 7: Add Input Validation for Prompts
```python
# prompt_builder.py: Add before line 100
def _sanitize_input(self, text: str) -> str:
    """Remove potentially dangerous control sequences."""
    if not text:
        return ""
    # Remove ChatML special tokens to prevent prompt injection
    for token in ["
