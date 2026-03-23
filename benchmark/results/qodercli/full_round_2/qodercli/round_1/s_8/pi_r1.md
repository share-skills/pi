# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 39.7s

---

Now let me conduct a thorough security analysis of all provided files:

## Security Audit Results: Inference Module

### 1. Issues Found

**api_server.py:**
- Line 35: **Hardcoded API key with default fallback** - `api_key` defaults to `"sk-guwen-default-key-2024"` if env var not set
- Line 67: **Overly permissive CORS** - `allow_origins=["*"]` allows any origin
- Line 68: **Credentials enabled with wildcard CORS** - `allow_credentials=True` combined with wildcard origins is a security risk
- Line 70-71: **Wildcard methods and headers** - `allow_methods=["*"]` and `allow_headers=["*"]` 
- Line 139: **API key logged in plaintext** - `logger.info(f"Server starting with API key: {config.api_key}")`
- Line 166-177: **No API key authentication** - `/v1/chat/completions` endpoint has no auth check despite config having api_key
- Line 229: **Unchecked dictionary access** - `chunk["choices"][0]` can raise KeyError/IndexError
- Line 263: **Config file path not validated** - `load_config()` accepts arbitrary paths without validation

**model_loader.py:**
- Line 24: **trust_remote_code=True by default** - Allows arbitrary code execution from model hub
- Line 77: **Silent exception handling** - torch.cuda.empty_cache() failure silently ignored (minor)

**prompt_builder.py:**
- Line 122: **Unsafe string formatting** - Uses `.format()` on user-controlled text, potential template injection
- Line 157: **Token estimation bypass** - No validation on input text length before processing

---

### 2. Hidden Issues

**Security:**
- Line 35 (api_server.py): Default API key pattern `sk-guwen-default-key-2024` reveals key format to attackers
- Line 166-220: No rate limiting on `/v1/chat/completions` endpoint - DoS vulnerability
- Line 229-247: `_stream_completion` yields error chunks without proper sanitization - potential information leakage
- Line 254-265: `load_config()` vulnerable to path traversal attacks (e.g., `../../../etc/passwd`)

**Performance:**
- Line 155 (api_server.py): `app.state.request_count += 1` is not thread-safe - race condition under concurrent load
- Line 122 (prompt_builder.py): No max length enforcement before building prompt - could cause OOM

**Resource Management:**
- Line 77 (model_loader.py): `torch.cuda.empty_cache()` may not actually free memory immediately
- Line 263 (api_server.py): HTTP client created but never explicitly closed - potential connection leak

**Input Validation:**
- Line 99-108 (ChatCompletionRequest): No validation on `messages` content length - could overflow context window
- Line 122 (prompt_builder.py): User text passed directly to `.format()` - if user includes `{text}` literally, could break template

**Configuration:**
- Line 24 (model_loader.py): `trust_remote_code=True` should never be default - allows model authors to execute arbitrary code
- Line 30 (api_server.py): `workers: int = 4` hardcoded, should be configurable based on CPU cores

---

### 3. Root Cause

| Issue | Root Cause | Location |
|-------|-----------|----------|
| Hardcoded credentials | Development convenience overrode security; default fallback undermines env var pattern | api_server.py:35 |
| Permissive CORS | Copy-paste from development config; no security review | api_server.py:67-71 |
| Missing auth check | API key defined but never validated in middleware or routes | api_server:166-220 |
| trust_remote_code | vLLM default carried over without security consideration | model_loader.py:24 |
| Unsafe string formatting | Python's `.format()` used without escaping user input | prompt_builder.py:122 |
| No rate limiting | Production requirements not considered in initial design | api_server.py:166 |
| Plaintext logging | Debug logging left in production code | api_server.py:139 |

---

### 4. Recommended Fix

**Fix 1: Remove hardcoded API key default**
```python
# Before (line 35):
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# After:
api_key: Optional[str] = os.environ.get("GUWEN_API_KEY")
# Require explicit None check or raise in production
```

**Fix 2: Restrictive CORS configuration**
```python
# Before (lines 67-71):
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Fix 3: Add API key authentication middleware**
```python
# Add after line 73:
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if credentials.credentials != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# Then protect routes:
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
```

**Fix 4: Disable trust_remote_code by default**
```python
# Before (line 24):
trust_remote_code: bool = True

# After:
trust_remote_code: bool = False  # Only enable for verified models
```

**Fix 5: Safe string formatting**
```python
# Before (line 122):
user_content = template.format(text=text)

# After:
from string import Template
template_obj = Template(template)
user_content = template_obj.safe_substitute(text=text)
```

**Fix 6: Remove sensitive logging**
```python
# Before (line 139):
logger.info(f"Server starting with API key: {config.api_key}")

# After:
logger.info("Server starting with API key configured")
# Or remove entirely
```

**Fix 7: Add input validation**
```python
# Add to ChatCompletionRequest validation:
@validator('messages')
def validate_messages(cls, v):
    if not v:
        raise ValueError("Messages cannot be empty")
    if len(v) > 100:
        raise ValueError("Too many messages (max 100)")
    total_length = sum(len(m.content) for m in v)
    if total_length > 100000:
        raise ValueError("Total content too long")
    return v
```

---

### 5. Steps Taken

1. **Read api_server.py completely** - Identified 8 security issues including hardcoded credentials, CORS misconfiguration, missing authentication, and unsafe config loading
2. **Read model_loader.py completely** - Found `trust_remote_code=True` default which allows arbitrary code execution
3. **Read prompt_builder.py completely** - Discovered unsafe string formatting with `.format()` on user input
4. **Analyzed data flow** - Traced request from `/v1/chat/completions` through prompt building to vLLM backend
5. **Checked configuration patterns** - Verified that security-critical settings have unsafe defaults
6. **Reviewed error handling** - Found unchecked dictionary access and silent exception swallowing
7. **Examined logging statements** - Discovered plaintext credential logging
8. **Cross-referenced OWASP Top 10** - Mapped findings to known vulnerability categories

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual code review | Line-by-line security analysis of all 4 files |
| OWASP Top 10 mapping | Categorize vulnerabilities by severity |
| Data flow analysis | Trace user input through the system |
| Configuration audit | Review all default values and environment variable usage |

---

### 7. Verification

**Immediate verification commands:**

```bash
# 1. Check for hardcoded secrets
grep -rn "default-key\|sk-guwen" src/inference/

# 2. Verify CORS configuration
grep -A5 "CORSMiddleware" src/inference/api_server.py

# 3. Check trust_remote_code setting
grep "trust_remote_code" src/inference/model_loader.py

# 4. Search for plaintext credential logging
grep -n "logger.*api_key\|logger.*password\|logger.*secret" src/inference/

# 5. Verify authentication is missing
grep -n "verify_api_key\|Depends.*security\|HTTPBearer" src/inference/api_server.py
```

**Expected output before fix:**
```
src/inference/api_server.py:35:    api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")
src/inference/api_server.py:67:        allow_origins=["*"],
src/inference/model_loader.py:24:    trust_remote_code: bool = True
src/inference/api_server.py:139:    logger.info(f"Server starting with API key: {config.api_key}")
```

**Risk Summary:**

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 Critical | 3 | Hardcoded API key, trust_remote_code=True, no authentication |
| 🟡 High | 4 | Wildcard CORS, path traversal, template injection, credential logging |
| 🟠 Medium | 3 | Race condition, resource leaks, missing rate limits |

**Recommendation**: Do NOT deploy to production until Critical and High severity issues are resolved.
