# Scenario 8: Inference Config Security Audit
## Condition: pua | Run: 1
## Duration: 73.95s

---

## Security Audit Report: Inference Module

### 1. Issues Found (Direct Security Concerns)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Hardcoded API Key with Weak Default** | CRITICAL | `api_server.py:51`, `inference_config.yaml:16` |
| 2 | **API Key Logged in Plaintext** | HIGH | `api_server.py:122` |
| 3 | **Permissive CORS Policy** | HIGH | `api_server.py:116-119` |
| 4 | **No Authentication Middleware** | CRITICAL | `api_server.py` (entire file) |
| 5 | **trust_remote_code=True** | HIGH | `model_loader.py:28` |
| 6 | **No Input Validation/Sanitization** | MEDIUM | `api_server.py:147-205` |
| 7 | **No Rate Limiting** | MEDIUM | `api_server.py` (entire file) |
| 8 | **Plaintext HTTP for Backend Communication** | MEDIUM | `api_server.py:44` |
| 9 | **Sensitive Data Exposure via Health Endpoint** | LOW | `api_server.py:207-215` |
| 10 | **Binding to All Interfaces (0.0.0.0) by Default** | MEDIUM | `api_server.py:40` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| H1 | **Docker Compose Hardcoded Credentials** | MINIO uses `minioadmin/minioadmin` default credentials | `docker-compose.yml:22-23` |
| H2 | **Config File Contains Sensitive Comments** | Config explicitly notes security issues but remains unchanged | `inference_config.yaml:6,15` |
| H3 | **Environment Variable Fallback to Weak Default** | Even when `GUWEN_API_KEY` is set, fallback exists in code | `api_server.py:51` |
| H4 | **No Request Size Limits** | Potential DoS via large payloads | `api_server.py` |
| H5 | **UUID Predictability** | Uses `uuid4().hex[:12]` - truncated UUIDs reduce entropy | `api_server.py:199,282` |
| H6 | **Error Messages May Leak Internal Details** | HTTPError details exposed directly | `api_server.py:228` |
| H7 | **No TLS/HTTPS Configuration** | All communication is plaintext | Entire module |
| H8 | **Prompt Injection Vulnerability** | User content directly inserted into ChatML format without escaping | `api_server.py:248`, `prompt_builder.py:123` |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Security-by-Obscurity Mindset**: The code assumes internal deployment equals safe deployment. Hardcoded defaults and lack of authentication assume no malicious actors.

2. **Missing Security Layer Architecture**: No defense-in-depth. The module lacks:
   - Authentication middleware
   - Input validation layer
   - Rate limiting
   - Audit logging

3. **Insecure Defaults**: Every configuration option defaults to the least secure setting (open CORS, plaintext HTTP, trust_remote_code=True).

4. **Logging Sensitive Data**: The api_key is logged at startup (`api_server.py:122`), which means it appears in:
   - Console output
   - Log files
   - Container logs (accessible to anyone with Docker access)

5. **Prompt Injection Vector**: The `_build_prompt` function directly concatenates user-provided `msg.content` into ChatML format without any sanitization. An attacker could inject `
