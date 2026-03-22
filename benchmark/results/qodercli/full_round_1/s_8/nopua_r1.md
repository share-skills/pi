# Scenario 8: Inference Config Security Audit
## Condition: nopua | Run: 1
## Duration: 68.85s

---

## Security Audit Report: Inference Module

### 1. Issues Found

#### **CRITICAL: Hardcoded API Key with Secret Logging** 
- **Location:** `api_server.py:51`, `api_server.py:122`, `inference_config.yaml:16`
- **Issue:** Default API key `sk-guwen-default-key-2024` is hardcoded and logged at startup
- **Risk:** API credentials exposed in logs, allowing unauthorized access
- **Evidence:**
  ```python
  # api_server.py:51
  api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")
  
  # api_server.py:122
  logger.info(f"Server starting with API key: {config.api_key}")
  ```

#### **CRITICAL: No API Key Authentication Enforcement**
- **Location:** `api_server.py:147-205` (`/v1/chat/completions` endpoint)
- **Issue:** API key is defined but **never validated** on any endpoint
- **Risk:** Complete lack of authentication - anyone can access the API

#### **HIGH: Insecure CORS Configuration**
- **Location:** `api_server.py:114-120`
- **Issue:** CORS allows all origins with credentials
- **Risk:** CSRF attacks, credential theft from any website
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Any origin
      allow_credentials=True,  # With cookies/auth
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

#### **HIGH: trust_remote_code=True (Code Injection Risk)**
- **Location:** `model_loader.py:28`, `inference_config.yaml:29`
- **Issue:** Loading models with `trust_remote_code=True` allows arbitrary code execution
- **Risk:** Malicious model checkpoints can execute arbitrary code on your system
  ```python
  trust_remote_code: bool = True  # Default enabled!
  ```

#### **HIGH: Plaintext API Key in Config File**
- **Location:** `inference_config.yaml:16`
- **Issue:** API key stored in plaintext in version-controlled config file
- **Risk:** Credential leakage through git history, CI/CD logs

#### **MEDIUM: Missing TLS for Backend Communication**
- **Location:** `api_server.py:44`, `inference_config.yaml:7`
- **Issue:** vLLM backend uses unencrypted HTTP
- **Risk:** Man-in-the-middle attacks if network is compromised
  ```python
  vllm_url: str = "http://localhost:8001"  # No TLS
  ```

#### **MEDIUM: No Input Validation on User Content**
- **Location:** `api_server.py:235-253` (`_build_prompt`), `prompt_builder.py:84-130`
- **Issue:** User messages directly concatenated into prompts without sanitization
- **Risk:** Prompt injection attacks, jailbreaking

#### **MEDIUM: No Request Rate Limiting**
- **Location:** `api_server.py:147-205`
- **Issue:** No rate limiting or DoS protection on endpoints
- **Risk:** Resource exhaustion, denial of service

---

### 2. Hidden Issues Discovered

#### **Information Disclosure via Logging**
- **Location:** `api_server.py:122-123`
- **Issue:** Sensitive configuration (API keys, backend URLs) logged at INFO level
- **Impact:** Anyone with log access sees credentials

#### **No SSL Verification for HTTP Client**
- **Location:** `api_server.py:127`
- **Issue:** `httpx.AsyncClient` created without explicit SSL verification settings
- **Impact:** Potential MITM vulnerability if HTTPS is used

#### **Missing Error Handling Leakage**
- **Location:** `api_server.py:227-228` (`/v1/embeddings`)
- **Issue:** Raw exception messages returned to clients
  ```python
  raise HTTPException(status_code=502, detail=str(e))  # Exposes internal errors
  ```

#### **Prompt Truncation Without Warning**
- **Location:** `prompt_builder.py:152-160`
- **Issue:** Silent truncation may cut off critical safety instructions
- **Impact:** Could bypass system prompt safeguards

---

### 3. Root Cause Analysis

| Root Cause | Related Issues |
|------------|----------------|
| **Security as afterthought** | No authentication enforcement, missing input validation, no rate limiting |
| **Development defaults in production code** | Hardcoded API key, `trust_remote_code=True`, permissive CORS |
| **Insecure logging practices** | Credentials logged at startup, verbose error messages |
| **Missing defense-in-depth** | Single points of failure, no TLS, no request validation |

---

### 4. Recommended Fixes

#### Immediate (Before Production):

1. **Remove hardcoded API key** - Require environment variable, fail if not set
   ```python
   api_key: str = os.environ["GUWEN_API_KEY"]  # No fallback
   ```

2. **Implement API key validation middleware**
   ```python
   @app.middleware("http")
   async def validate_api_key(request: Request, call_next):
       api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
       if api_key != app.state.config.api_key:
           raise HTTPException(status_code=401, detail="Invalid API key")
       return await call_next(request)
   ```

3. **Restrict CORS to known origins**
   ```python
   allow_origins=["https://your-domain.com"],  # Not ["*"]
   ```

4. **Disable trust_remote_code by default**
   ```python
   trust_remote_code: bool = False  # Only enable for verified models
   ```

5. **Remove sensitive data from logs**
   ```python
   logger.info("Server starting...")  # No API key in logs
   ```

#### Short-term:

6. Add rate limiting (e.g., `slowapi` or custom middleware)
7. Implement input sanitization for user content
8. Add TLS for backend communication (or use Unix socket for localhost)
9. Use secrets management for API keys (Vault, AWS Secrets Manager)
10. Return generic error messages to clients

---

### 5. Steps Taken

1. Read all 4 source files in the inference module
2. Searched for credential patterns (api_key, password, secret, token)
3. Identified hardcoded credentials and logging issues
4. Analyzed CORS middleware configuration
5. Checked model loading security settings (`trust_remote_code`)
6. Reviewed config file for plaintext secrets
7. Examined HTTP client configuration for SSL/TLS settings
8. Analyzed error handling patterns for information disclosure

---

### 6. Tools Used

- `Read` tool: Read all 4 Python source files + YAML config
- `Grep` tool: Searched for security-sensitive patterns (credentials, CORS, logging, trust_remote_code)
- `Glob` tool: Located config files and .env files

---

### 7. Verification

**Findings verified by direct code evidence:**
- ✅ Hardcoded API key confirmed at `api_server.py:51`
- ✅ Credential logging confirmed at `api_server.py:122`
- ✅ Permissive CORS confirmed at `api_server.py:116`
- ✅ `trust_remote_code=True` confirmed at `model_loader.py:28`
- ✅ Plaintext secret in config confirmed at `inference_config.yaml:16`
- ✅ No auth enforcement verified by reading entire `create_app()` function
- ✅ Error message leakage confirmed at `api_server.py:228`

**Not verified by execution:**
- ❌ Did not run the server (would require GPU/vLLM setup)
- ❌ Did not attempt actual prompt injection attacks

---

### Summary Table

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 CRITICAL | 2 | Hardcoded+logged API key, No auth enforcement |
| 🟠 HIGH | 3 | Insecure CORS, trust_remote_code, Plaintext config |
| 🟡 MEDIUM | 4 | No TLS, No input validation, No rate limiting, Error disclosure |
| **Total** | **9** | |

**Recommendation:** Do NOT deploy to production until CRITICAL and HIGH issues are resolved.
