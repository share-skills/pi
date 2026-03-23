# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 2
## Duration: 33.49s

---

Now let me conduct a systematic security audit across all four dimensions (Security, Performance, Correctness, Readability).

## Security Audit Analysis

### 1. Issues Found

| ID | Severity | File:Line | Issue |
|----|----------|-----------|-------|
| SEC-01 | 🔴 Blocker | api_server.py:35 | **Hardcoded API key with default fallback** - `api_key` has default value `"sk-guwen-default-key-2024"` that's used if env var not set |
| SEC-02 | 🔴 Blocker | api_server.py:97-101 | **Overly permissive CORS** - `allow_origins=["*"]` allows any origin to make requests |
| SEC-03 | 🔴 Blocker | api_server.py:168 | **API key logged at startup** - `logger.info(f"Server starting with API key: {config.api_key}")` exposes secret in logs |
| SEC-04 | 🟡 Suggestion | model_loader.py:26 | **trust_remote_code=True by default** - Allows arbitrary code execution from model files |
| SEC-05 | 🟡 Suggestion | api_server.py:145-159 | **No input validation on max_tokens/temperature** - User can request excessive resources |
| SEC-06 | 🟡 Suggestion | api_server.py:204-210 | **Embedding endpoint proxies arbitrary JSON** - No validation of request body before proxying |
| SEC-07 | 🟡 Suggestion | prompt_builder.py:119 | **No sanitization of RAG context** - Context injection could enable prompt injection attacks |
| SEC-08 | ⚪ Nit | api_server.py:32 | **Sensitive config in dataclass without protection** - API key stored as plain string |

### 2. Hidden Issues

| ID | Category | File:Line | Issue |
|----|----------|-----------|-------|
| HID-01 | Resource Leak | api_server.py:106 | **httpx.AsyncClient never closed** - No shutdown handler to close `app.state.http_client` |
| HID-02 | Thread Safety | api_server.py:107 | **Race condition on request_count** - `app.state.request_count += 1` not atomic in async context |
| HID-03 | Error Handling | api_server.py:168-170 | **Bare except in HTTPError handling** - Catches all exceptions, may hide bugs |
| HID-04 | Performance | prompt_builder.py:160-163 | **Inefficient token estimation** - O(n) iteration per character, called repeatedly without caching |
| HID-05 | Boundary | prompt_builder.py:155-158 | **Truncation breaks UTF-8** - Character-based truncation may split multi-byte characters |
| HID-06 | Configuration | model_loader.py:22-25 | **Hardcoded GPU memory utilization 0.9** - May cause OOM on systems with less VRAM |
| HID-07 | Unused Import | api_server.py:15 | **`Any` imported but never used** - Cleanup needed |
| HID-08 | Cross-Platform | model_loader.py:89-93 | **torch.cuda import without check** - Will fail on CPU-only systems |
| HID-09 | Information Disclosure | api_server.py:186-191 | **Health endpoint exposes internal config** - Reveals vLLM backend URL |
| HID-10 | Prompt Injection | prompt_builder.py:94-96 | **User content directly interpolated** - No escaping of special ChatML tokens in user input |

### 3. Root Cause

| Issue | Root Cause |
|-------|------------|
| SEC-01, SEC-03, SEC-08 | **Security not treated as primary concern** - API keys treated as convenience settings rather than secrets |
| SEC-02 | **Development configuration shipped to production** - Wildcard CORS is acceptable for dev but dangerous for prod |
| SEC-04 | **Trust boundary violation** - Remote code execution enabled by default without explicit opt-in |
| SEC-05, SEC-06 | **Missing input validation layer** - No schema validation or rate limiting on resource-intensive parameters |
| SEC-07, HID-10 | **No defense in depth for prompts** - User input trusted without sanitization against prompt injection |
| HID-01 | **Missing lifecycle management** - FastAPI lifespan handlers not implemented for resource cleanup |
| HID-02 | **Async concurrency oversight** - Shared mutable state accessed without synchronization |
| HID-05 | **String vs byte confusion** - Truncation operates on characters instead of encoded bytes |

### 4. Recommended Fix

#### SEC-01: Hardcoded API Key (api_server.py:35)
```python
# Before:
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# After:
api_key: str = os.environ.get("GUWEN_API_KEY")

def __post_init__(self):
    if not self.api_key:
        raise ValueError(
            "GUWEN_API_KEY environment variable must be set. "
            "Generate a secure key for production deployment."
        )
```

#### SEC-02: Overly Permissive CORS (api_server.py:97-101)
```python
# Before:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# After:
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  # Restrict to needed methods
    allow_headers=["Authorization", "Content-Type"],
)
```

#### SEC-03: API Key Logging (api_server.py:168)
```python
# Before:
logger.info(f"Server starting with API key: {config.api_key}")

# After:
logger.info(f"Server starting with API key: {'*' * 8}...{config.api_key[-4:]}")
```

#### SEC-04: trust_remote_code (model_loader.py:26)
```python
# Before:
trust_remote_code: bool = True

# After:
trust_remote_code: bool = False  # Must be explicitly enabled with warning
```

#### HID-01: Resource Leak (api_server.py:106)
```python
# Add lifespan handler:
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=config.timeout)
    yield
    await app.state.http_client.aclose()

app = FastAPI(..., lifespan=lifespan)
```

#### HID-02: Race Condition (api_server.py:107)
```python
# Before:
app.state.request_count += 1

# After:
import asyncio
app.state.request_lock = asyncio.Lock()

# In handler:
async with app.state.request_lock:
    app.state.request_count += 1
```

#### HID-10: Prompt Injection (prompt_builder.py:94-96)
```python
# Add sanitization:
def _sanitize_chatml_content(self, content: str) -> str:
    """Remove or escape ChatML special tokens from user content."""
    content = re.sub(r'
