# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 84.42s

---

Now I have a complete picture. Let me provide the structured summary:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Port mismatch causing "Connection refused"** | P0 - Critical | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| **2** | **Config file explicitly documents bug but unfixed** | P1 - High | `rag_config.yaml:5-6`, `docker-compose.yml:42-44` |
| **3** | **No connection retry/timeout logic** | P2 - Medium | `rag_pipeline.py:155-170` |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **H1** | **Unused imports** - `os`, `time`, `field`, `Tuple` imported but never used | Code quality | `rag_pipeline.py:22-26` |
| **H2** | **Tests mock connections** - Tests use `@patch("src.retrieval.rag_pipeline.connections")` so they never catch real port mismatches | Tests pass but production fails | `test_rag_pipeline.py:28-91` |
| **H3** | **Empty embeddings returns wrong shape** - `np.array([])` returns 1D array but callers expect 2D `(n, dim)` | Potential runtime error | `rag_pipeline.py:111` |
| **H4** | **Collection load called on every search** - `load()` is expensive and should be cached | Performance issue | `rag_pipeline.py:303` |
| **H5** | **Exception silently swallowed in create_collection** - Lines 227-231 catch exceptions and fall through, potentially masking schema issues | Reliability risk | `rag_pipeline.py:227-231` |
| **H6** | **No context manager support** - `close()` exists but is never auto-called, resource leak risk | Resource management | `rag_pipeline.py:380-385` |
| **H7** | **Hardcoded query prefix for BGE** - Line 114 hardcodes Chinese query prefix, no consideration for model changes | Maintainability | `rag_pipeline.py:114` |
| **H8** | **No validation of chunk data** - `index_chunks` assumes `text` key exists, will throw KeyError | Robustness | `rag_pipeline.py:253` |
| **H9** | **Developers knew about bug but left it** - Comments in both config files document the port issue as "intentional for Scenario 3" but never fixed | Technical debt | `docker-compose.yml:42-44`, `rag_config.yaml:5-6` |

---

### 3. Root Cause

**Primary Root Cause:** Docker Compose maps host port **19531** to container port **19530**, but both `RAGConfig` default and `rag_config.yaml` specify port **19530**.

**Evidence:**

```yaml
# docker-compose.yml:42-45
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
- "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

```yaml
# configs/rag_config.yaml:5-6
# Docker compose default maps 19531:19530 in this project.
milvus_port: 19530   # BUG: Docker uses 19531
```

**Why embedder works standalone:** The `EmbeddingModel` class uses `sentence-transformers` locally with no network dependency on Milvus. It only fails when `RAGPipeline.__init__()` calls `_connect()` at line 152.

**Vector Dimension Verification:** ✅ **CORRECT** - BGE-large-zh-v1.5 uses **1024 dimensions**, confirmed by web search and code (`BGE_EMBEDDING_DIM = 1024` at line 42).

---

### 4. Recommended Fix

#### Immediate Fix (Required)

**Option A: Fix the config file** (Recommended - single line change)

```yaml
# configs/rag_config.yaml:6
milvus_port: 19531   # Changed from 19530 to match Docker host port
```

**Option B: Fix Docker Compose** (Alternative)

```yaml
# docker-compose.yml:45
- "19530:19530"   # Use standard port on host
```

Then restart:
```bash
docker-compose down && docker-compose up -d
```

#### Additional Fixes (Should be applied)

1. **Add connection retry with timeout:**
```python
def _connect(self, max_retries: int = 3, retry_delay: float = 1.0):
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
                logger.error(f"Failed to connect after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying...: {e}")
            time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
```

2. **Remove unused imports** from `rag_pipeline.py:22-26`

3. **Fix empty embeddings shape** at line 111:
```python
if not texts:
    return np.empty((0, self.config.embedding_dim))  # Return 2D array
```

---

### 5. Steps Taken

1. **Read `rag_pipeline.py`** - Analyzed connection logic (`_connect` at lines 155-170), config defaults (lines 46-76), embedding dimension constant (line 42)
2. **Read `docker-compose.yml`** - Discovered port mapping `19531:19530` and explicit comments documenting the known bug
3. **Read `rag_config.yaml`** - Confirmed config uses port 19530 with comment acknowledging it's wrong for Docker
4. **Read `test_rag_pipeline.py`** - Discovered tests mock `connections`, hiding the real issue
5. **Read `index_corpus.py`** - Verified how config is loaded in production scripts (line 34)
6. **Web search** - Confirmed BAAI/bge-large-zh-v1.5 embedding dimension is 1024
7. **Cross-referenced comments** - Found developers intentionally left this bug for "Scenario 3" testing

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (rag_pipeline.py, docker-compose.yml, rag_config.yaml, test files, index_corpus.py) |
| `Glob` | Locate configuration files (docker-compose.yml, rag_config.yaml) |
| `Grep` | Search for all port references across codebase |
| `WebSearch` | Verify BAAI/bge-large-zh-v1.5 embedding dimension |

---

### 7. Verification

**Verified findings:**

| Finding | Verification Method | Status |
|---------|---------------------|--------|
| Port mismatch causes connection refused | Cross-checked docker-compose.yml mapping `19531:19530` against RAGConfig default `19530` | ✅ CONFIRMED |
| Config file has known bug | Comment in rag_config.yaml line 6 explicitly states `# BUG: Docker uses 19531` | ✅ CONFIRMED |
| Embedding dimension 1024 is correct | Web search + code inspection confirms BGE-large-zh-v1.5 = 1024 | ✅ CONFIRMED CORRECT |
| Tests don't catch this issue | Test file uses `@patch("src.retrieval.rag_pipeline.connections")` mocking | ✅ CONFIRMED |
| Developers knew but didn't fix | Comments in both docker-compose.yml and rag_config.yaml document the bug as "intentional for Scenario 3" | ✅ CONFIRMED |

**Quick verification command:**

```bash
# Test connection to correct port
python -c "from pymilvus import connections; connections.connect(host='localhost', port=19531); print('Connected!')"
```

Or fix the config and run:
```bash
sed -i 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml
python scripts/index_corpus.py --chunks ./data/chunks --config configs/rag_config.yaml
```

---

### Summary

The **"Connection refused"** error is caused by a **port mismatch**: Docker Compose exposes Milvus on host port `19531`, but the RAG pipeline configuration defaults to port `19530`. This was **intentionally left as a documented bug** (per comments in both config files) for "Scenario 3" testing purposes but was never fixed.

**Embedding dimensions are correct** at 1024 for BGE-large-zh-v1.5.
