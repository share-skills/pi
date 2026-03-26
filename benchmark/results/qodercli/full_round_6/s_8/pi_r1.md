# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 42.2s

---

Now I have a complete picture. Let me compile the security audit report:

---

## 🔒 Security Audit Report: Inference Module

### 1. Issues Found

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | 🔴 Blocker | `api_server.py:51` | **Hardcoded default API key** - Falls back to `sk-guwen-default-key-2024` if env var not set |
| 2 | 🔴 Blocker | `api_server.py:122` | **API key logged in plaintext** - `logger.info(f"Server starting with API key: {config.api_key}")` |
| 3 | 🔴 Blocker | `api_server.py:114-120` | **Overly permissive CORS** - `allow_origins=["*"]` with `allow_credentials=True` |
| 4 | 🔴 Blocker | `api_server.py:147-205` | **No authentication on /v1/chat/completions** - API key defined but never validated |
| 5 | 🟡 Suggestion | `api_server.py:44` | **vLLM backend uses HTTP without TLS** - `http://localhost:8001` (acceptable for localhost only) |
| 6 | 🟡 Suggestion | `model_loader.py:28` | **trust_remote_code=True by default** - Allows arbitrary code execution from model files |
| 7 | 🟡 Suggestion | `api_server.py:217-228` | **/v1/embeddings endpoint lacks auth** - Same issue as chat completions |
| 8 | ⚪ Nit | `prompt_builder.py:123` | **History injection without validation** - `msg['role']` and `msg['content']` accessed without null checks |

---

### 2. Hidden Issues

| # | Category | Location | Issue |
|---|----------|----------|-------|
| H1 | 🔒 Security | `api_server.py:324` | **Module-level app instantiation** - `app = create_app()` at import time bypasses config control |
| H2 | 🔒 Security | `api_server.py:245-253` | **Prompt injection vulnerability** - User content directly concatenated into ChatML format without sanitization |
| H3 | ⚡ Performance | `api_server.py:127` | **httpx client created once, never closed** - Potential connection pool exhaustion |
| H4 | ⚡ Performance | `prompt_builder.py:159` | **Naive truncation by character count** - May cut mid-token, causing malformed prompts |
| H5 | ✅ Correctness | `api_server.py:198-203` | **Response schema mismatch** - `created` field uses ISO format but OpenAI expects Unix timestamp (int) |
| H6 | ✅ Correctness | `api_server.py:154` | **Non-thread-safe counter** - `app.state.request_count += 1` has race condition in async context |
| H7 | 🔒 Security | `configs/inference_config.yaml:16` | **Plaintext API key in config file** - Committed to version control |

---

### 3. Root Cause

**Primary Root Cause:** The module was designed for **local development**, not production deployment. Security controls are superficial:

1. **Authentication theater** (`api_server.py:51`): An `api_key` config exists but is **never actually used** to validate incoming requests. The key is merely logged at startup.

2. **Missing authorization middleware** (`api_server.py:147-205`): The `/v1/chat/completions` endpoint accepts any request without checking `Authorization` headers. Compare to OpenAI's actual API which requires `Bearer sk-...` header validation.

3. **CORS misconfiguration** (`api_server.py:114-120`): The combination of `allow_origins=["*"]` + `allow_credentials=True` is explicitly warned against in FastAPI/docs—it allows any website to make authenticated requests on behalf of users.

4. **Trust boundary violations** (`prompt_builder.py:84-130`): User-supplied content is directly interpolated into prompt templates without escaping special sequences like `
