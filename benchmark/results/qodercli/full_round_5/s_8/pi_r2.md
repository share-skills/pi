# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 88.03s

---

## 🔒 Security Audit Report: Inference Module

### 1. Issues Found

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔴 blocker | Hardcoded API key with default fallback | `api_server.py:L51` |
| 2 | 🔴 blocker | API key logged in plaintext at startup | `api_server.py:L130` |
| 3 | 🔴 blocker | No authentication middleware on API endpoints | `api_server.py:L155-L247` |
| 4 | 🔴 blocker | Overly permissive CORS policy (allow all origins) | `api_server.py:L122-L128` |
| 5 | 🟡 high | Hardcoded plaintext API key in config file | `inference_config.yaml:L16` |
| 6 | 🟡 high | HTTP without TLS for backend communication | `api_server.py:L44`, `inference_config.yaml:L7` |
| 7 | 🟡 high | `trust_remote_code=True` enables arbitrary code execution | `model_loader.py:L28,L77` |
| 8 | 🟠 medium | No input validation on user messages (prompt injection risk) | `api_server.py:L165`, `prompt_builder.py:L84-L130` |
| 9 | 🟠 medium | Health endpoint exposes internal architecture | `api_server.py:L226-L234` |
| 10 | ⚪ low | Unused import (`re`, `datetime`) | `api_server.py:L22`, `prompt_builder.py:L12` |

---

### 2. Hidden Issues

| # | Category | Issue | Location |
|---|----------|-------|----------|
| 1 | Security | API key can be bypassed - no actual validation logic exists anywhere | Entire codebase |
| 2 | Security | SSRF risk: vLLM URL is configurable but not validated (could point to internal services) | `api_server.py:L176,L242` |
| 3 | Security | Prompt injection: User content directly concatenated into prompts without sanitization | `prompt_builder.py:L123,L126` |
| 4 | Security | No rate limiting on API endpoints (DoS vulnerability) | `api_server.py:L155-L247` |
| 5 | Security | Request body parsed without size limits (memory exhaustion risk) | `api_server.py:L239` |
| 6 | Performance | Character-based token estimation is inaccurate (~4x error margin) | `prompt_builder.py:L162-L170` |
| 7 | Correctness | No timeout handling for streaming responses | `api_server.py:L275-L326` |
| 8 | Correctness | Missing null check for `chunk["choices"][0]` in stream handler | `api_server.py:L309` |
| 9 | Resource | httpx.AsyncClient never closed (connection pool leak) | `api_server.py:L135` |
| 10 | Config | `gpu_memory_utilization=0.9` may cause OOM on multi-process setups | `model_loader.py:L25` |

---

### 3. Root Cause

**3.1 Authentication Bypass (Issues 1,2,3,5)**
- `api_server.py:L51` - Default API key hardcoded: `"sk-guwen-default-key-2024"`
- `api_server.py:L130` - API key logged: `logger.info(f"Server starting with API key: {config.api_key}")`
- No `Depends()` or middleware to validate `Authorization` header on any endpoint

**3.2 CORS Misconfiguration (Issue 4)**
- `api_server.py:L124` - `allow_origins=["*"]` permits any origin
- `api_server.py:L125` - `allow_credentials=True` combined with wildcard origin is a security anti-pattern

**3.3 Code Execution Risk (Issue 7)**
- `model_loader.py:L28,L77` - `trust_remote_code=True` allows model authors to execute arbitrary Python code

**3.4 Input Validation Gap (Issue 8, Hidden 3)**
- `prompt_builder.py:L123` - User content directly interpolated: `f"
