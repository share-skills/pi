# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 1
## Duration: 116.11s

---

## Investigation Complete

---

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Port mismatch causing connection refused** | CRITICAL | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| **2** | **Config file port not updated** | CRITICAL | `configs/rag_config.yaml:6` |
| **3** | **RAGConfig default port hardcoded to 19530** | HIGH | `src/retrieval/rag_pipeline.py:50` |
| **4** | **No connection retry logic or timeout handling** | MEDIUM | `src/retrieval/rag_pipeline.py:155-170` |
| **5** | **Embedding dimension is correct (1024)** | VERIFIED OK | `src/retrieval/rag_pipeline.py:42` |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| **H1** | **Test mocks hide real connection failures** - Tests use `@patch("src.retrieval.rag_pipeline.connections")` so they never catch the actual port mismatch | Tests pass but production fails |
| **H2** | **index_corpus.py loads config incorrectly** - Line 34 merges YAML data directly without proper nested key handling when `rag:` prefix exists | May cause config loading issues |
| **H3** | **Collection creation has silent fallback** - Lines 227-231 catch exceptions and fall through, potentially masking schema issues | Data corruption risk |
| **H4** | **No health check before connection** - Code attempts immediate connection without verifying Milvus is actually ready | Race condition on startup |
| **H5** | **Comments acknowledge bug but no fix applied** - Both `docker-compose.yml:42-45` and `rag_config.yaml:5-6` have comments documenting the port issue, but it was never fixed | Technical debt intentionally left |

---

### 3. Root Cause

**Primary Root Cause:** Docker Compose maps host port `19531` to container port `19530`, but both `RAGConfig` default and `rag_config.yaml` specify port `19530`. When running via Docker, the application tries to connect to `localhost:19530`, but Milvus is exposed on `localhost:19531`.

**Evidence from code:**
```yaml
# docker-compose.yml:42-45
- "19531:19530"   # <-- Intentional port mismatch for Scenario 3
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
```

```yaml
# configs/rag_config.yaml:5-6
# Docker compose default maps 19531:19530 in this project.
milvus_port: 19530   # BUG: Docker uses 19531
```

**Why embedder works standalone:** The `EmbeddingModel` class uses `sentence-transformers` locally and has no network dependency on Milvus. It only fails when the RAG pipeline tries to establish a Milvus connection during initialization.

---

### 4. Recommended Fix

#### Immediate Fix (Required)

**Option A: Fix the config file** (Recommended)
```yaml
# configs/rag_config.yaml
milvus_port: 19531   # Changed from 19530 to match Docker host port
```

**Option B: Fix Docker Compose** (Alternative)
```yaml
# docker-compose.yml
- "19530:19530"   # Map host 19530 to container 19530
```

#### Additional Fixes (Should be applied)

1. **Add connection retry with timeout:**
```python
def _connect(self):
    """Establish connection to Milvus with retry."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            connections.connect(
                alias=self.config.milvus_alias,
                host=self.config.milvus_host,
                port=self.config.milvus_port,
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.config.milvus_host}:{self.config.milvus_port}")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Milvus after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying...: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

2. **Update test to verify actual connection** (not just mocks)

---

### 5. Steps Taken

1. **Read the full rag_pipeline.py** - Analyzed connection logic, config defaults, and embedding setup
2. **Read docker-compose.yml** - Found explicit comment about port mismatch being intentional for "Scenario 3"
3. **Read rag_config.yaml** - Confirmed config has documented bug (port 19530 instead of 19531)
4. **Searched all files for port references** - Found 16 matches across 6 files showing consistent 19530 usage
5. **Read test file** - Discovered tests mock connections, hiding the real issue
6. **Read index_corpus.py** - Verified how config is loaded in production scripts
7. **Web search for BGE embedding dimension** - Confirmed 1024 is correct for bge-large-zh-v1.5
8. **Cross-referenced comments** - Found that developers knew about this bug but left it unfixed

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read rag_pipeline.py, docker-compose.yml, rag_config.yaml, test files, index_corpus.py |
| `Glob` | Locate configuration files and Python sources |
| `Grep` | Search for all port references (19530/19531) across codebase |
| `WebSearch` | Verify BAAI/bge-large-zh-v1.5 embedding dimension is 1024 |
| `Bash` | Attempt to check Docker container status |

---

### 7. Verification

**Verified findings:**

| Finding | Verification Method | Status |
|---------|---------------------|--------|
| Port mismatch causes connection refused | Cross-checked docker-compose.yml mapping `19531:19530` against RAGConfig default `19530` | CONFIRMED |
| Config file has known bug | Comment in rag_config.yaml line 6 explicitly states `# BUG: Docker uses 19531` | CONFIRMED |
| Embedding dimension 1024 is correct | Web search confirmed BAAI/bge-large-zh-v1.5 outputs 1024-dim embeddings | CONFIRMED CORRECT |
| Tests don't catch this issue | Test file uses `@patch("src.retrieval.rag_pipeline.connections")` mocking | CONFIRMED |
| Developers knew but didn't fix | Comments in both docker-compose.yml and rag_config.yaml document the bug | CONFIRMED |

**Proof of issue:**
```bash
# The error occurs because:
# 1. Docker exposes Milvus on localhost:19531
# 2. Application connects to localhost:19530
# 3. Nothing is listening on 19530 → Connection refused
```

---

### Summary

The **"Connection refused"** error is caused by a **port mismatch**: Docker Compose exposes Milvus on host port `19531`, but the RAG pipeline configuration defaults to port `19530`. This was **intentionally left as a bug** (per comments in both files) for "Scenario 3" testing purposes but was never fixed.

**Embedding dimensions are correct** at 1024 for BGE-large-zh-v1.5.
