# Scenario 8: Inference Config Security Audit
## Condition: nopua | Run: 2
## Duration: 52.32s

---

## Security Audit Report: Inference Module

Based on my analysis of the provided source code, I've identified multiple security concerns. Here's my comprehensive findings:

---

## 1. Issues Found

### **CRITICAL: Hardcoded API Key with Weak Default** (`api_server.py:36`)
```python
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")
```
- **Risk**: The default API key is predictable and publicly known (it's in the source code)
- **Impact**: Anyone can access the API using the hardcoded default key
- **Location**: `api_server.py:36`

### **CRITICAL: No API Key Validation Implemented** (`api_server.py`)
- The `api_key` is stored in config but **never validated** on any endpoint
- No authentication middleware or dependency is used to protect endpoints
- **Impact**: All endpoints are completely open to the internet if deployed with `--host 0.0.0.0`

### **HIGH: Overly Permissive CORS Configuration** (`api_server.py:84-89`)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Any origin can make requests
    allow_credentials=True,  # Credentials can be sent cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Risk**: Combined with `allow_credentials=True`, this enables CSRF attacks from any website
- **Impact**: Malicious websites can make authenticated requests on behalf of users

### **HIGH: Logging Sensitive Information** (`api_server.py:95`)
```python
logger.info(f"Server starting with API key: {config.api_key}")
```
- **Risk**: API keys are written to logs in plaintext
- **Impact**: Anyone with log access can retrieve the API key

### **MEDIUM: No Input Validation on User-Provided Data** (`api_server.py:134-147`)
- The `user` field in `ChatCompletionRequest` is accepted but never sanitized or validated
- No rate limiting, no input length limits beyond what Pydantic provides
- **Impact**: Potential for prompt injection, DoS via large payloads

### **MEDIUM: trust_remote_code=True** (`model_loader.py:26`)
```python
trust_remote_code: bool = True
```
- **Risk**: Allows execution of arbitrary Python code from downloaded models
- **Impact**: If the model repository is compromised, attackers can execute arbitrary code on your infrastructure

### **MEDIUM: No Health Check Authentication** (`api_server.py:178-184`)
- The `/health` endpoint exposes internal information (model name, request count, backend URL) without authentication
- **Impact**: Information disclosure that aids reconnaissance

### **LOW: Debug-Level Information in Responses** (`api_server.py:170`)
- Error messages from vLLM backend are directly returned to clients
- **Impact**: May leak internal infrastructure details

---

## 2. Hidden Issues Beyond the Ask

### **HIDDEN #1: No Rate Limiting**
- No rate limiting on any endpoint
- A single attacker can exhaust GPU resources with repeated requests
- **Impact**: DoS vulnerability, potential cost explosion if running on cloud

### **HIDDEN #2: No Request Size Limits**
- `max_tokens` defaults to 2048 but can be overridden by clients
- No explicit limit on message count or total request size
- **Impact**: Memory exhaustion, GPU OOM crashes

### **HIDDEN #3: Unsafe YAML Loading Pattern** (`api_server.py:252-260`)
```python
def load_config(config_path: str) -> InferenceConfig:
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)  # Uses safe_load, but...
```
- While `yaml.safe_load` is used correctly here, the function accepts arbitrary file paths
- **Impact**: Path traversal if user can control `config_path` argument

### **HIDDEN #4: No TLS/HTTPS Configuration**
- Server binds to `0.0.0.0` by default with no HTTPS support
- **Impact**: All traffic (including API keys if ever implemented) transmitted in plaintext

### **HIDDEN #5: Resource Exhaustion via Concurrent Requests**
- No concurrency limits or request queuing
- `workers: int = 4` is defined but not enforced for the actual server
- **Impact**: GPU memory exhaustion under load

### **HIDDEN #6: Streaming Endpoint Error Handling** (`api_server.py:206-241`)
- Errors during streaming are caught but only logged, not properly handled
- The stream may hang indefinitely on backend failure
- **Impact**: Resource leaks, potential for hanging connections

### **HIDDEN #7: Prompt Injection Surface** (`prompt_builder.py`)
- User-provided `text` is directly inserted into prompts without sanitization
- Context from RAG is trusted without validation
- **Impact**: Jailbreak attacks, prompt injection, data exfiltration via crafted inputs

---

## 3. Root Causes

| Root Cause | Issues Caused |
|-----------|---------------|
| **Security not designed in from start** | No auth, no rate limiting, no input validation |
| **Development convenience over production security** | Hardcoded keys, permissive CORS, logging secrets |
| **Missing security middleware layer** | No centralized auth, rate limiting, or request filtering |
| **Trust boundary confusion** | Treating all client input as trusted, trusting remote code blindly |
| **No defense in depth** | Single points of failure, no fallback protections |

---

## 4. Recommended Fixes

### **Immediate (Before Production)**

1. **Remove hardcoded API key** - Require environment variable, fail if not set:
   ```python
   api_key: str = os.environ["GUWEN_API_KEY"]  # Raise KeyError if not set
   ```

2. **Implement API key validation** on all endpoints:
   ```python
   from fastapi import Security, HTTPException
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

   security = HTTPBearer()

   async def verify_api_key(creds: HTTPAuthorizationCredentials = Security(security)):
       if creds.credentials != config.api_key:
           raise HTTPException(status_code=401, detail="Invalid API key")
   ```

3. **Fix CORS configuration**:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # Specific origins only
       allow_credentials=False,  # Or implement proper CSRF protection
       allow_methods=["POST", "GET"],  # Explicit methods
       allow_headers=["Authorization", "Content-Type"],  # Explicit headers
   )
   ```

4. **Remove API key from logs**:
   ```python
   logger.info(f"Server starting with API key configured: {'***' if config.api_key else 'MISSING'}")
   ```

5. **Set `trust_remote_code=False`** unless absolutely necessary:
   ```python
   trust_remote_code: bool = False  # Only enable for verified, audited models
   ```

### **Short-Term**

6. **Add rate limiting** (e.g., using `slowapi` or custom middleware)
7. **Add request size limits** via FastAPI middleware
8. **Add health check authentication** or remove sensitive info
9. **Implement proper error handling** that doesn't leak internals
10. **Add TLS support** for production deployments

### **Long-Term**

11. **Implement prompt sanitization** for user inputs
12. **Add monitoring/alerting** for suspicious patterns
13. **Implement request queuing** with backpressure for GPU protection
14. **Add audit logging** for all API calls (without sensitive data)

---

## 5. Steps Taken

1. Read and analyzed all four source files line-by-line
2. Identified authentication/authorization gaps
3. Checked for secure configuration practices
4. Analyzed input validation boundaries
5. Examined error handling patterns
6. Reviewed CORS and network exposure settings
7. Checked for secret management practices
8. Identified resource exhaustion vectors
9. Analyzed prompt building for injection surfaces

---

## 6. Tools Used

- Manual code review (static analysis)
- OWASP Top 10 mental checklist
- Security pattern recognition (hardcoded secrets, CORS, auth)
- Attack surface mapping (entry points → data flow → outputs)

---

## 7. Verification

I verified my findings by:
- Cross-referencing line numbers in the source code
- Confirming the API key is defined but never used for validation
- Verifying CORS middleware configuration allows all origins + credentials
- Confirming `trust_remote_code=True` is the default in `ModelConfig`
- Checking that no rate limiting or request size middleware exists

---

## Summary Table

| Severity | Issue | File | Line | Status |
|---------|-------|------|------|--------|
| 🔴 CRITICAL | Hardcoded API key default | api_server.py | 36 | Needs fix |
| 🔴 CRITICAL | No API key validation | api_server.py | All endpoints | Needs fix |
| 🟠 HIGH | Permissive CORS + credentials | api_server.py | 84-89 | Needs fix |
| 🟠 HIGH | Logging sensitive data | api_server.py | 95 | Needs fix |
| 🟡 MEDIUM | No input validation | api_server.py | 134+ | Needs review |
| 🟡 MEDIUM | trust_remote_code=True | model_loader.py | 26 | Needs fix |
| 🟡 MEDIUM | Unauthenticated health endpoint | api_server.py | 178-184 | Needs fix |
| 🟢 LOW | Error detail leakage | api_server.py | 170 | Should fix |
| 🟢 HIDDEN | No rate limiting | - | Global | Needs feature |
| 🟢 HIDDEN | No request size limits | - | Global | Needs feature |
| 🟢 HIDDEN | Prompt injection surface | prompt_builder.py | 90+ | Needs review |

---

**Recommendation**: Do **NOT** deploy to production until at least the CRITICAL and HIGH severity issues are addressed. The current code is suitable for local development only.
