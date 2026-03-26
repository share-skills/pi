# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 100.84s

---

Now I have completed a thorough investigation. Let me compile the comprehensive security audit report:

---

## 🔒 Security Audit Report: Inference Module

### 1. Issues Found

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔴 Blocker | API key logged in plaintext at startup | `api_server.py:122` |
| 2 | 🔴 Blocker | Hardcoded default API key with weak fallback | `api_server.py:51`, `inference_config.yaml:16` |
| 3 | 🔴 Blocker | CORS allows all origins with credentials | `api_server.py:114-119` |
| 4 | 🟡 High | vLLM backend uses unencrypted HTTP | `api_server.py:44`, `inference_config.yaml:7` |
| 5 | 🟡 High | `trust_remote_code=True` enables arbitrary code execution | `model_loader.py:28,77` |
| 6 | 🟡 High | No API key validation on endpoints | `api_server.py:147-228` |
| 7 | 🟡 High | YAML config loads without validation | `api_server.py:310-318` |
| 8 | 🟠 Medium | Unused import (`datetime` imported but not used directly) | `api_server.py:22` |
| 9 | 🟠 Medium | Prompt injection vulnerability via user content | `prompt_builder.py:115-126` |
| 10 | 🟠 Medium | No input validation on message roles | `api_server.py:61-64` |
| 11 | ⚪ Low | Token estimation is inaccurate for mixed scripts | `prompt_builder.py:162-170` |
| 12 | ⚪ Low | Model path is hardcoded without validation | `model_loader.py:21` |

---

### 2. Hidden Issues (Beyond Surface Ask)

| # | Category | Issue | Location |
|---|----------|-------|----------|
| H1 | 🔒 Security | **SSRF risk**: vLLM URL is user-configurable without whitelist | `api_server.py:44` |
| H2 | 🔒 Security | **No rate limiting**: Request counter exists but no throttling | `api_server.py:128,154` |
| H3 | 🔒 Security | **Error information leakage**: Full exception messages exposed to clients | `api_server.py:228` |
| H4 | 🔒 Security | **Module-level app instantiation**: Creates global state at import time | `api_server.py:324` |
| H5 | ⚡ Performance | **No connection pooling**: httpx client created once but no pool config | `api_server.py:127` |
| H6 | ⚡ Performance | **Streaming error handling swallows exceptions**: Bare except continues silently | `prompt_builder.py:300-301` |
| H7 | 📖 Correctness | **Race condition**: `request_count += 1` is not thread-safe | `api_server.py:154` |
| H8 | 📖 Correctness | **Type mismatch**: `created` field type differs between model (str) and usage (int) | `api_server.py:97` vs `api_server.py:200` |
| H9 | 🔧 Config | **Config key mismatch**: YAML uses `model:` section but code expects `inference:` | `inference_config.yaml:22-30` |

---

### 3. Root Cause Analysis

**RC1 - Credential Management Failure** (`api_server.py:51,122`)
```python
# Line 51: Hardcoded default with insecure fallback
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# Line 122: Logs secret to stdout
logger.info(f"Server starting with API key: {config.api_key}")
```
**Root Cause**: Security-by-obscurity anti-pattern; secrets should never have defaults or be logged.

**RC2 - Missing Authentication Layer** (`api_server.py:147-228`)
All endpoints (`/v1/chat/completions`, `/v1/embeddings`, `/health`) lack authentication middleware despite `api_key` being defined in config.

**RC3 - Overly Permissive CORS** (`api_server.py:114-119`)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Any origin can access
    allow_credentials=True,     # With cookies/auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Root Cause**: Development configuration shipped to production.

**RC4 - Remote Code Execution Risk** (`model_loader.py:28,77`)
```python
trust_remote_code: bool = True  # Allows model authors to execute arbitrary Python
```
**Root Cause**: Convenience over security; enables supply chain attacks via malicious model weights.

**RC5 - Input Validation Gaps** (`api_server.py:61-64`, `prompt_builder.py:115-126`)
- Message `role` accepts any string (no enum validation)
- User content is concatenated into prompts without sanitization
- No max length validation before processing

---

### 4. Recommended Fix

#### Fix 1: Secure Credential Handling
```python
# api_server.py:51
# BEFORE:
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# AFTER:
api_key: str = os.environ.get("GUWEN_API_KEY")
if not api_key:
    raise ValueError("GUWEN_API_KEY environment variable is required")
```

```python
# api_server.py:122
# BEFORE:
logger.info(f"Server starting with API key: {config.api_key}")

# AFTER:
logger.info(f"Server starting with API key: {'*' * 8}")
```

#### Fix 2: Add Authentication Middleware
```python
# api_server.py: Add after line 128
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    if not creds or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials

# Then protect endpoints:
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completion(request: ChatCompletionRequest):
    ...
```

#### Fix 3: Restrict CORS
```python
# api_server.py:114-119
# BEFORE:
allow_origins=["*"],
allow_credentials=True,

# AFTER:
allow_origins=["https://trusted-domain.com"],  # Explicit whitelist
allow_credentials=False,
allow_methods=["GET", "POST"],
allow_headers=["Authorization", "Content-Type"],
```

#### Fix 4: Disable trust_remote_code by Default
```python
# model_loader.py:28
# BEFORE:
trust_remote_code: bool = True

# AFTER:
trust_remote_code: bool = False  # Only enable for verified models
```

#### Fix 5: Add Input Validation
```python
# api_server.py:61-64
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(...)  # Enum validation
    content: str = Field(..., max_length=32768)  # Max length
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read all 4 inference module files | Identified module structure |
| 2 | Initially thought issue was limited to logging → **Upon closer inspection**, found 12 distinct issues across security/performance/correctness |
| 3 | Read `inference_config.yaml` | Confirmed hardcoded credentials, documented security warnings in comments |
| 4 | Searched for credential patterns (`api_key`, `secret`, `token`) | Found hardcoded API key in code + config |
| 5 | Searched for dangerous patterns (`trust_remote_code`, `eval`, `exec`) | Found `trust_remote_code=True` enabling RCE |
| 6 | Searched for insecure protocols (`http://`) | Found unencrypted vLLM backend URL |
| 7 | **Strategy变更**: Expanded from single-file analysis → cross-module search | Found SSRF risk, missing auth, race conditions |
| 8 | Validated Pydantic model definitions | Found type mismatch (`created`: str vs int), missing enum validation |
| 9 | Analyzed CORS configuration | Found overly permissive settings for production |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 4 Python source files + YAML config |
| `Glob` | Located config files (`inference_config.yaml`) |
| `Bash (grep)` | Searched for sensitive patterns, insecure URLs, dangerous functions |
| Manual code review |逐行审查 security-critical code paths |

---

### 7. Verification

#### Immediate Verification Commands:

```bash
# 1. Check if API key is logged (run server, check output)
cd /Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project
python -m src.inference.api_server --config configs/inference_config.yaml 2>&1 | grep -i "api key"
# EXPECTED: Should show masked key or no key

# 2. Test CORS headers (should NOT allow * with credentials)
curl -H "Origin: https://evil.com" -I http://localhost:8000/health
# EXPECTED: Access-Control-Allow-Origin should NOT be *

# 3. Test authentication bypass (should require API key)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}'
# EXPECTED: 401 Unauthorized

# 4. Verify trust_remote_code setting
grep -n "trust_remote_code" src/inference/model_loader.py
# EXPECTED: Should be False by default
```

#### Security Scan Command:
```bash
# Run bandit security linter
pip install bandit
bandit -r src/inference/ -lll
```

---

### 📋 交付确认

| Item | Status |
|------|--------|
| ✅ Target Match | Security audit completed for `src/inference/` module |
| ✅ Boundary Coverage | All 4 files analyzed; 12 surface issues + 9 hidden issues identified |
| ✅ Risk Control | Blocker/High/Medium/Low severity分级标注; fix recommendations provided |
| ❓ Requires Attention | Config section mismatch (`model:` vs `inference:`) needs clarification |

**Production Deployment Recommendation**: 🔴 **DO NOT DEPLOY** until Blocker issues (1-3) are resolved.
