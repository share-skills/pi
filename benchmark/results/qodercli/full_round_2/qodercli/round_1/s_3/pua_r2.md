# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 92.42s

---

Now I have all the information needed. Let me compile my investigation findings:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **1** | **Port mismatch: Docker maps 19531:19530, but RAG config uses 19530** | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` | **CRITICAL** - Causes "Connection refused" |
| **2** | **No connection retry logic or timeout handling** | `rag_pipeline.py:155-170` | HIGH - Fails immediately on transient errors |
| **3** | **Collection.load() called on every search** | `rag_pipeline.py:303` | MEDIUM - Unnecessary latency per query |

---

### 2. Hidden Issues

| # | Issue | Impact |
|---|-------|--------|
| **H1** | **Vector dimension verification is hardcoded** - `BGE_EMBEDDING_DIM = 1024` in code matches actual model (confirmed: BAAI/bge-large-zh-v1.5 outputs 1024-dim vectors) | **VERIFIED CORRECT** - No dimension mismatch |
| **H2** | **No health check before connection** - Code attempts to connect without verifying Milvus is reachable | May cause confusing errors |
| **H3** | **Test file confirms wrong default** - `test_rag_pipeline.py:11` asserts port 19530 is correct, reinforcing the bug | Test validates incorrect behavior |

---

### 3. Root Cause

**The Docker Compose configuration intentionally creates a port mismatch:**

```yaml
# docker-compose.yml:42-45
ports:
  # NOTE: Host port is 19531 but container port is 19530.
  # The RAG config defaults to 19530 — this WILL cause connection failures.
  - "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

When running via Docker:
- Milvus listens on port **19530** inside the container
- Docker maps host port **19531** → container port **19530**
- Client must connect to **localhost:19531** from outside Docker

The `RAGConfig` defaults to `milvus_port: int = 19530` (`rag_pipeline.py:50`), which works for native installations but fails when Milvus runs in Docker with the mapped port.

**The embedder working standalone is unrelated** — it doesn't connect to Milvus, only to Hugging Face for model downloads.

---

### 4. Recommended Fix

**Option A (Recommended): Update config to match Docker setup**
```yaml
# configs/rag_config.yaml
milvus_port: 19531  # Changed from 19530
```

**Option B: Fix docker-compose to use standard port**
```yaml
# docker-compose.yml
ports:
  - "19530:19530"  # Use standard port
```

**Option C: Add environment-aware defaults in code**
```python
# rag_pipeline.py - detect Docker environment
@dataclass
class RAGConfig:
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: int = int(os.getenv("MILVUS_PORT", 19531))  # Default for Docker
```

---

### 5. Steps Taken

1. **Read source code** - Analyzed `rag_pipeline.py` (386 lines) for connection logic
2. **Examined Docker configuration** - Found intentional port mismatch comment in `docker-compose.yml`
3. **Checked RAG config** - Confirmed `milvus_port: 19530` in `rag_config.yaml`
4. **Verified embedding dimension** - Confirmed BGE-large-zh-v1.5 outputs 1024-dim vectors (matches code)
5. **Reviewed test files** - Found tests validate incorrect port behavior
6. **Searched official documentation** - Verified model specification

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (rag_pipeline.py, docker-compose.yml, configs, tests) |
| `Glob` | Locate YAML and Python files |
| `WebSearch` | Verify BGE embedding dimension from official sources |
| `Bash` | Check Docker status |

---

### 7. Verification

**Evidence collected:**
- ✅ `docker-compose.yml:45` explicitly states `"19531:19530"` with comment about intentional mismatch
- ✅ `rag_config.yaml:6` has `milvus_port: 19530` with comment `# BUG: Docker uses 19531`
- ✅ `rag_pipeline.py:42` defines `BGE_EMBEDDING_DIM = 1024` — **matches actual model** (verified via web search: Xinference docs confirm 1024 dimensions)
- ✅ Embedding dimension is **NOT the issue** — both code and model use 1024

**Why embedder works standalone:** The `EmbeddingModel` class connects to Hugging Face to download/load the model, not to Milvus. Only `RAGPipeline._connect()` attempts Milvus connection.

---

## Summary

| Category | Finding |
|----------|---------|
| **Primary Issue** | Port mismatch: Docker exposes Milvus on 19531, client tries 19530 |
| **Vector Dimensions** | ✅ Correct — 1024 matches BGE-large-zh-v1.5 specification |
| **Root Cause** | Configuration inconsistency between Docker mapping and client config |
| **Fix** | Set `milvus_port: 19531` in `configs/rag_config.yaml` or update `RAGConfig` default |
