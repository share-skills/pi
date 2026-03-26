# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 54.75s

---

## Security Audit Report: Inference Module

Based on my analysis of the provided source code, here is a comprehensive security audit:

---

### 1. Issues Found

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | 🔴 Blocker | `api_server.py:L62` | **Hardcoded API key** with weak default (`sk-guwen-default-key-2024`) |
| 2 | 🔴 Blocker | `api_server.py:L83-L88` | **CORS misconfiguration** - `allow_origins=["*"]` allows any origin |
| 3 | 🔴 Blocker | `api_server.py:L140-L141` | **No authentication** on `/v1/chat/completions` endpoint |
| 4 | 🟡 Suggestion | `api_server.py:L59` | **API key logged** at startup - secrets in logs |
| 5 | 🟡 Suggestion | `api_server.py:L200` | **Missing input validation** - no max length check on messages |
| 6 | 🟡 Suggestion | `api_server.py:L267` | **trust_remote_code=True** default - arbitrary code execution risk |
| 7 | 🟡 Suggestion | `model_loader.py:L24` | **No path traversal protection** - model_path accepts arbitrary paths |
| 8 | ⚪ Nit | `api_server.py:L59` | **Verbose error messages** may leak internal structure |

---

### 2. Hidden Issues

| # | Category | Location | Issue |
|---|----------|----------|-------|
| 1 | 🔒 Security | `api_server.py:L140` | No rate limiting - DoS vulnerability |
| 2 | 🔒 Security | `api_server.py:L200` | No request size limit - potential memory exhaustion |
| 3 | 🔒 Security | `api_server.py:L267` | Streaming error handler yields error chunks without sanitization |
| 4 | ⚡ Performance | `prompt_builder.py:L117` | Token estimation is naive (~1.5/char) - may cause truncation issues |
| 5 | ⚡ Performance | `api_server.py:L97` | `request_count` unbounded - memory leak over time |
| 6 | 🧠 Correctness | `api_server.py:L62` | Default API key is predictable - trivial to guess |
| 7 | 🧠 Correctness | `model_loader.py:L24` | No GPU memory bounds check - may OOM on small GPUs |
| 8 | 🧠 Correctness | `prompt_builder.py:L80` | No prompt injection protection - user can override system prompt |

---

### 3. Root Cause

| Issue | Root Cause | Code Reference |
|-------|------------|----------------|
| Hardcoded credentials | Default fallback when env var not set | `api_server.py:L62` |
| CORS misconfiguration | Wildcard origins for development convenience | `api_server.py:L83-L88` |
| No auth on endpoints | API key stored but never validated | `api_server.py:L140` |
| Secret logging | Config logged verbatim at startup | `api_server.py:L59` |
| Missing input validation | No schema constraints on request body | `api_server.py:L140+` |
| trust_remote_code risk | vLLM default enabled without warning | `model_loader.py:L24` |
| Path traversal | No validation of model_path parameter | `model_loader.py:L20` |
| Prompt injection | System prompt can be overridden via history | `prompt_builder.py:L117` |

---

### 4. Recommended Fix

#### Fix 1: Remove hardcoded API key + add validation
```python
# api_server.py:L62
# BEFORE:
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# AFTER:
api_key: str = os.environ.get("GUWEN_API_KEY")
# Require API key in production; None means auth disabled

# Add validation:
def __post_init__(self):
    if self.api_key == "sk-guwen-default-key-2024":
        raise ValueError("Default API key not allowed in production")
```

#### Fix 2: Add authentication middleware
```python
# api_server.py:L140 - Add before chat_completion
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest, _: bool = Depends(verify_api_key)):
```

#### Fix 3: Restrict CORS
```python
# api_server.py:L83-L88
# BEFORE:
allow_origins=["*"]

# AFTER (config-driven):
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
allow_origins=allowed_origins if allowed_origins else ["https://trusted-domain.com"]
```

#### Fix 4: Don't log secrets
```python
# api_server.py:L59
# BEFORE:
logger.info(f"Server starting with API key: {config.api_key}")

# AFTER:
logger.info(f"Server starting, API key configured: {bool(config.api_key)}")
```

#### Fix 5: Add input validation
```python
# api_server.py:L95 - Add to ChatCompletionRequest
class ChatCompletionRequest(BaseModel):
    # ... existing fields ...
    
    @field_validator('messages')
    def validate_messages(cls, v):
        if len(v) > 100:
            raise ValueError("Max 100 messages per request")
        for msg in v:
            if len(msg.content) > 32000:
                raise ValueError("Message content too long")
        return v
```

#### Fix 6: Secure trust_remote_code
```python
# model_loader.py:L24
# BEFORE:
trust_remote_code: bool = True

# AFTER:
trust_remote_code: bool = False  # Default to False for security
# Add environment override:
trust_remote_code: bool = os.environ.get("TRUST_REMOTE_CODE", "false").lower() == "true"
```

#### Fix 7: Add path validation
```python
# model_loader.py:L20
import pathlib

def __post_init__(self):
    model_path = pathlib.Path(self.model_path).resolve()
    # Prevent path traversal
    if not str(model_path).startswith(os.getcwd()):
        raise ValueError("model_path must be within current directory")
```

---

### 5. Steps Taken

1. **Read all 4 source files** - Analyzed complete codebase structure
2. **Identified authentication gaps** - API key defined but never used for validation
3. **Checked CORS configuration** - Found wildcard allowing any origin
4. **Examined logging practices** - Discovered secret exposure in logs
5. **Reviewed model loading** - Found trust_remote_code and path traversal risks
6. **Analyzed prompt building** - Identified prompt injection vectors
7. **Cross-referenced OWASP Top 10** - Mapped findings to known vulnerability patterns
8. **Evaluated production readiness** - Assessed deployment risks

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual code review | Line-by-line security analysis |
| OWASP Top 10 checklist | Vulnerability pattern matching |
| FastAPI security best practices | Authentication/rate limiting guidance |
| Python security guidelines | Path traversal, trust_remote_code analysis |

---

### 7. Verification

**Recommended verification commands:**

```bash
# 1. Test authentication bypass (should fail after fix)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"guwen-llm","messages":[{"role":"user","content":"test"}]}'

# 2. Test CORS headers (should not return * after fix)
curl -I -X OPTIONS http://localhost:8000/v1/chat/completions \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST"

# 3. Verify no secrets in logs
grep -r "API key" logs/ | grep -v "configured:"

# 4. Test rate limiting (after implementation)
for i in {1..100}; do curl http://localhost:8000/health; done

# 5. Test path traversal (should fail after fix)
python -c "from src.inference.model_loader import ModelConfig; ModelConfig(model_path='../../../etc/passwd')"
```

---

## Summary

| Category | Count |
|----------|-------|
| 🔴 Blocker | 3 |
| 🟡 Suggestion | 4 |
| ⚪ Nit | 1 |
| **Hidden Issues** | 8 |

**Critical priorities before production:**
1. Implement authentication on all API endpoints
2. Remove hardcoded API key default
3. Restrict CORS to trusted domains
4. Stop logging secrets
5. Add input validation (message count, content length)

Would you like me to create a PR with these security fixes?
