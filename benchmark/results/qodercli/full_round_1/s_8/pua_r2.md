# Scenario 8: Inference Config Security Audit
## Condition: pua | Run: 2
## Duration: 61.28s

---

Now I have completed my investigation. Let me compile the comprehensive security audit report:

---

## Security Audit Report: Inference Module (`src/inference/`)

### 1. Issues Found (Critical → Low Severity)

#### **CRITICAL: Hardcoded API Key with Weak Default**
- **Location**: `api_server.py:51`, `inference_config.yaml:16`
- **Issue**: Default API key `sk-guwen-default-key-2024` is hardcoded and publicly visible
- **Impact**: Any attacker can authenticate to the API using the default key
- **Code**:
  ```python
  api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")
  ```

#### **CRITICAL: API Key Logged in Plaintext**
- **Location**: `api_server.py:122`
- **Issue**: API key is written to application logs at startup
- **Impact**: Credentials exposed in log files, log aggregation systems, debugging outputs
- **Code**:
  ```python
  logger.info(f"Server starting with API key: {config.api_key}")
  ```

#### **CRITICAL: No Authentication Enforcement on Endpoints**
- **Location**: `api_server.py:147-205` (chat_completion endpoint)
- **Issue**: The `api_key` config exists but is **never validated** on incoming requests. Test confirms this behavior (`test_no_auth_required`)
- **Impact**: All endpoints are completely open to the internet
- **Evidence**: Test at `tests/test_api_server.py:32-50` explicitly verifies no auth is required

#### **HIGH: Permissive CORS Configuration**
- **Location**: `api_server.py:114-120`
- **Issue**: CORS allows all origins (`*`), all methods, all headers with credentials
- **Impact**: Enables CSRF attacks, credential theft from any website
- **Code**:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

#### **HIGH: trust_remote_code=True**
- **Location**: `model_loader.py:28`, `inference_config.yaml:29`
- **Issue**: Loading models with arbitrary remote code execution enabled
- **Impact**: Malicious model checkpoints can execute arbitrary code on the server
- **Code**:
  ```python
  trust_remote_code: bool = True
  ```

#### **MEDIUM: Unencrypted Backend Communication**
- **Location**: `api_server.py:44`, `inference_config.yaml:7`
- **Issue**: vLLM backend uses plaintext HTTP (`http://localhost:8001`)
- **Impact**: Traffic can be intercepted if localhost is compromised; no TLS in production
- **Note**: Config comment acknowledges this: "hardcoded localhost without TLS (security issue)"

#### **MEDIUM: Server-Side Request Forgery (SSRF) Risk**
- **Location**: `api_server.py:217-228` (/v1/embeddings endpoint)
- **Issue**: Proxies arbitrary JSON body to backend without validation
- **Impact**: Attackers could potentially access internal network resources through the backend
- **Code**:
  ```python
  @app.post("/v1/embeddings")
  async def create_embedding(request: Request):
      body = await request.json()
      response = await app.state.http_client.post(f"{config.vllm_url}/v1/embeddings", json=body)
  ```

#### **MEDIUM: Prompt Injection Vulnerability**
- **Location**: `api_server.py:235-253` (_build_prompt), `prompt_builder.py:84-130`
- **Issue**: User input directly concatenated into prompts without sanitization
- **Impact**: Attackers can inject malicious instructions via user messages
- **Code**:
  ```python
  parts.append(f"
