# Scenario 8: Inference Config Security Audit
## Condition: pua | Run: 1
## Duration: 76.2s

---

Excellent! I now have a comprehensive view of the security issues. Let me document my findings:

---

## Security Audit Report: Inference Module

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Hardcoded API Key with Default Value** | CRITICAL | `api_server.py:51`, `inference_config.yaml:16` |
| 2 | **API Key Logged in Plaintext** | HIGH | `api_server.py:122` |
| 3 | **No Authentication Enforcement** | CRITICAL | `api_server.py:147-205` |
| 4 | **Overly Permissive CORS Policy** | HIGH | `api_server.py:114-120` |
| 5 | **SSRF Vulnerability via vLLM URL** | MEDIUM | `api_server.py:167-178` |
| 6 | **trust_remote_code=True by Default** | HIGH | `model_loader.py:28` |
| 7 | **No Input Validation on User Messages** | MEDIUM | `api_server.py:235-253` |
| 8 | **No Rate Limiting** | MEDIUM | Entire module |
| 9 | **Information Disclosure in Health Endpoint** | LOW | `api_server.py:207-215` |
| 10 | **HTTP Only (No TLS) for Backend Communication** | MEDIUM | `api_server.py:44`, `inference_config.yaml:7` |

---

### 2. Hidden Issues Discovered

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| H1 | **Config File Contains Hardcoded Secret** | HIGH | `inference_config.yaml:16` |
| H2 | **Comment Acknowledges Security Issue but Not Fixed** | INFO | `inference_config.yaml:6,15` |
| H3 | **No Resource Limits on Request Size** | MEDIUM | `ChatCompletionRequest` model |
| H4 | **Potential Prompt Injection via ChatML Tags** | MEDIUM | `api_server.py:235-253`, `prompt_builder.py:115-130` |
| H5 | **Error Messages May Leak Internal Details** | LOW | `api_server.py:183-184`, `227-228` |
| H6 | **Module-level app instantiation enables accidental import-side effects** | LOW | `api_server.py:324` |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Security not designed into architecture** - The module was built for functionality, not production security. Authentication exists in config but is never enforced.

2. **Insecure defaults** - Multiple security-critical settings default to insecure values:
   - `api_key` defaults to `"sk-guwen-default-key-2024"` instead of requiring env var
   - `trust_remote_code=True` enables arbitrary code execution from model files
   - `allow_origins=["*"]` permits any origin to make requests

3. **Missing security layers** - No defense-in-depth:
   - No authentication middleware
   - No rate limiting
   - No input sanitization
   - No request size limits

4. **Security-aware comments without action** - The config file explicitly warns about logging API keys but the code still logs them (`logger.info(f"Server starting with API key: {config.api_key}")`).

---

### 4. Recommended Fixes

#### Priority 1 (Critical - Fix Before Any Production Use)

| Issue | Fix |
|-------|-----|
| **No Authentication** | Add FastAPI `Depends` with API key validation on all `/v1/*` endpoints. Require `Authorization: Bearer <key>` header. |
| **Hardcoded API Key** | Remove default value. Require `GUWEN_API_KEY` environment variable. Fail startup if not set. |
| **API Key Logging** | Replace `logger.info(f"Server starting with API key: {config.api_key}")` with `logger.info("Server starting with configured API key")` or hash preview like `config.api_key[:8] + "..."` |

#### Priority 2 (High - Fix Before External Deployment)

| Issue | Fix |
|-------|-----|
| **CORS Wildcard** | Change `allow_origins=["*"]` to explicit allowed origins list from config. Consider `allow_origins=["https://your-domain.com"]` |
| **trust_remote_code=True** | Default to `False`. Only enable when explicitly required and model source is trusted. Document risks. |
| **Config File Secrets** | Remove `api_key` from YAML. Use only environment variables for secrets. |

#### Priority 3 (Medium - Address Before Scale)

| Issue | Fix |
|-------|-----|
| **No Rate Limiting** | Add `slowapi` or custom middleware with token bucket algorithm. Configure per-IP and per-API-key limits. |
| **No Input Validation** | Add Pydantic validators for message length, character limits, and reject messages containing raw `
