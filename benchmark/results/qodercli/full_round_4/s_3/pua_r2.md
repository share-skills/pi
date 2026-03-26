# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 95.23s

---

---

## Investigation Complete

---

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Port mismatch causing "Connection refused"** | CRITICAL | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| **2** | **Config file has documented but unfixed bug** | CRITICAL | `rag_config.yaml:5-6` |
| **3** | **Code default port hardcoded to 19530** | HIGH | `rag_pipeline.py:50` |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **H1** | **Tests mock connections, hiding real failures** - Tests use `@patch("src.retrieval.rag_pipeline.connections")` so CI never catches port mismatch | Tests pass but production fails | `test_rag_pipeline.py:28-51` |
| **H2** | **No connection retry/timeout logic** - Single failed connection attempt throws immediately with no retry | Race condition on startup, no resilience | `rag_pipeline.py:155-170` |
| **H3** | **Collection load() called on every search** - `_collection.load()` is expensive and called repeatedly without caching | Performance degradation | `rag_pipeline.py:303` |
| **H4** | **Silent exception fallback in create_collection()** - Exceptions are caught and silently ignored, potentially masking schema issues | Data corruption risk | `rag_pipeline.py:227-231` |
| **H5** | **Unused imports** - `os`, `time`, and `Tuple` imported but never used | Code quality issue | `rag_pipeline.py:22-25` |
| **H6** | **index_corpus.py config loading may be incorrect** - Line 34 merges YAML data directly; if YAML has `rag:` prefix, nested keys may not flatten correctly | Config loading bugs | `index_corpus.py:34` |
| **H7** | **Developers knew about the bug but left it unfixed** - Both `docker-compose.yml` and `rag_config.yaml` have comments documenting the port issue as intentional for "Scenario 3" testing | Technical debt intentionally left | `docker-compose.yml:42-45` |

---

### 3. Root Cause

**Primary Root Cause:** Docker Compose maps host port `19531` to container port `19530`, but both `RAGConfig` default and `rag_config.yaml` specify port `19530`.

**Evidence:**
```yaml
# docker-compose.yml:42-45
ports:
  - "19531:19530"   # Host:Container
  # NOTE: Host port is 19531 but container port is 19530.
  # The RAG config defaults to 19530 — this WILL cause connection failures.
  # Fix: set milvus_port: 19531 in rag_config.yaml
```

```yaml
# rag_config.yaml:5-6
# Docker compose default maps 19531:19530 in this project.
milvus_port: 19530   # BUG: Docker uses 19531
```

```python
# rag_pipeline.py:49-50
milvus_host: str = "localhost"
milvus_port: int = 19530  # Default matches neither Docker nor config comment
```

**Why embedder works standalone:** The `EmbeddingModel` class uses `sentence-transformers` locally with no network dependency on Milvus. It only fails when `RAGPipeline.__init__()` calls `_connect()` which attempts to connect to Milvus.

**Vector Dimensions:** ✅ **VERIFIED CORRECT** - BGE-large-zh-v1.5 uses **1024 dimensions**, confirmed by:
- Code: `BGE_EMBEDDING_DIM = 1024` (line 42)
- Config: `embedding_dim: 1024` (rag_config.yaml line 10)
- Web search confirmation: bge-large-zh-v1.5 specification shows 1024 dimensions

---

### 4. Recommended Fix

#### Immediate Fix (Required)

**Option A: Fix the config file** (Recommended - No code change)
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
sed -i '' 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml
```

Verify:
```bash
cat configs/rag_config.yaml | grep milvus_port
# Should output: milvus_port: 19531
```

**Option B: Fix Docker Compose** (Alternative - Changes exposed port)
```yaml
# docker-compose.yml:45
- "19530:19530"   # Map host 19530 to container 19530
```

#### Additional Fixes (Should be applied)

1. **Add connection retry with exponential backoff:**
```python
def _connect(self, max_retries: int = 5):
    """Establish connection to Milvus with retry."""
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
            wait_time = 2 ** attempt
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
```

2. **Cache collection load state** to avoid calling `load()` on every search.

3. **Update tests to verify actual connection** (not just mocks) or add integration test.

4. **Remove unused imports** from `rag_pipeline.py`:
```python
# Remove these lines:
import os
import time
# Remove Tuple from typing import
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `rag_pipeline.py` full source | Confirmed default port 19530, embedding dim 1024 |
| 2 | Read `docker-compose.yml` | Found explicit port mapping `19531:19530` with warning comment |
| 3 | Read `rag_config.yaml` | Confirmed config has documented bug (port 19530 instead of 19531) |
| 4 | Grep for all port references | Found 333 matches across 6+ files showing consistent 19530 usage |
| 5 | Read `test_rag_pipeline.py` | Discovered tests mock connections, hiding real issue |
| 6 | Read `index_corpus.py` | Verified how config is loaded in production scripts |
| 7 | Web search for BGE embedding dimension | Confirmed 1024 is correct for bge-large-zh-v1.5 |
| 8 | Cross-reference comments | Found developers knew about bug but left it unfixed for "Scenario 3" |
| 9 | Check Docker status | Docker not currently running (container not active) |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read rag_pipeline.py, docker-compose.yml, rag_config.yaml, test files, index_corpus.py |
| `Glob` | Locate configuration files and Docker configs |
| `Grep` | Search for all port references (19530/19531) across codebase |
| `WebSearch` | Verify BAAI/bge-large-zh-v1.5 embedding dimension is 1024 |
| `Bash` | Check Docker container status |
| `TodoWrite` | Track investigation progress |

---

### 7. Verification

**Verified findings:**

| Finding | Verification Method | Status |
|---------|---------------------|--------|
| Port mismatch causes connection refused | Cross-checked docker-compose.yml mapping `19531:19530` against RAGConfig default `19530` | CONFIRMED |
| Config file has known bug | Comment in rag_config.yaml line 6 explicitly states `# BUG: Docker uses 19531` | CONFIRMED |
| Embedding dimension 1024 is correct | Web search + code review confirmed BAAI/bge-large-zh-v1.5 outputs 1024-dim embeddings | CONFIRMED CORRECT |
| Tests don't catch this issue | Test file uses `@patch("src.retrieval.rag_pipeline.connections")` mocking | CONFIRMED |
| Developers knew but didn't fix | Comments in both docker-compose.yml and rag_config.yaml document the bug | CONFIRMED |

**Proof of issue:**
```
Docker exposes Milvus on localhost:19531
Application connects to localhost:19530
Nothing is listening on 19530 → Connection refused
```

---

### Summary

The **"Connection refused"** error is caused by a **port mismatch**: Docker Compose exposes Milvus on host port `19531`, but the RAG pipeline configuration defaults to port `19530`. This was **intentionally left as a bug** (per comments in both `docker-compose.yml:42-45` and `rag_config.yaml:5-6`) for "Scenario 3" testing purposes but was never fixed.

**Embedding dimensions are correct** at 1024 for BGE-large-zh-v1.5.

**Quick fix command:**
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
sed -i '' 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml
cat configs/rag_config.yaml | grep milvus_port  # Verify: should show 19531
```
