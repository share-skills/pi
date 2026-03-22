# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 108.95s

---

## 结构化调查报告

---

### 1. **Issues Found** (已发现问题)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Port mismatch: Docker maps 19531:19530, but RAG config defaults to 19530** | Critical | `docker-compose.yml:45`, `rag_config.yaml:6` |
| 2 | **No connection timeout configuration** - `connections.connect()` has no timeout parameter, causing indefinite hangs or immediate failures | High | `rag_pipeline.py:158-162` |
| 3 | **No retry mechanism** - Single connection attempt with no fallback | Medium | `rag_pipeline.py:155-170` |
| 4 | **Embedding dimension is CORRECT** (1024) - BGE-large-zh-v1.5 uses 1024 dimensions, verified via HuggingFace/ModelScope | N/A (Verified OK) | `rag_pipeline.py:42` |

---

### 2. **Hidden Issues** (额外发现的隐藏问题)

| # | Issue | Impact | Evidence |
|---|-------|--------|----------|
| 1 | **`collection.load()` called on EVERY search** - Inefficient, should load once during initialization | Performance degradation | `test_rag_pipeline.py:91` confirms `load()` called 3 times for 3 searches |
| 2 | **Config file has explicit BUG comment** - `milvus_port: 19530   # BUG: Docker uses 19531` was ignored | Root cause of connection failure | `rag_config.yaml:6` |
| 3 | **No health check before connection** - Code assumes Milvus is ready without verification | Race condition on startup | No `wait_for_healthy()` logic in `_connect()` |
| 4 | **Test explicitly verifies NO timeout field exists** - `test_no_connection_timeout_field()` proves this is a known gap | Technical debt acknowledged but unaddressed | `test_rag_pipeline.py:19-22` |
| 5 | **Exception handling falls through silently** - `create_collection()` catches exceptions but continues, potentially leaving `_collection` in undefined state | Data corruption risk | `rag_pipeline.py:227-231` |

---

### 3. **Root Cause** (根本原因)

**Primary Root Cause:**
The Docker Compose file explicitly maps host port **19531** to container port **19530**:
```yaml
# docker-compose.yml:42-45
ports:
  - "19531:19530"   # Host 19531 → Container 19530
```

However, the RAG configuration defaults to **19530**:
```yaml
# rag_config.yaml:6
milvus_port: 19530   # BUG: Docker uses 19531
```

When the client tries to connect to `localhost:19530`, nothing is listening there → **Connection refused**.

**Secondary Issue:**
The `pymilvus.connections.connect()` method does not support a `timeout` parameter (confirmed via official docs). The code has no wrapper logic to implement connection timeouts or retries, making it fragile in real-world deployments.

---

### 4. **Recommended Fix** (修复建议)

#### Fix 1: Correct the port configuration (Immediate fix)
```yaml
# configs/rag_config.yaml
milvus_port: 19531   # Changed from 19530 to match Docker mapping
```

#### Fix 2: Add connection timeout and retry logic (Code change)
```python
# src/retrieval/rag_pipeline.py
def _connect(self, max_retries: int = 3, retry_delay: float = 2.0):
    """Establish connection to Milvus with retry logic."""
    import time
    
    for attempt in range(max_retries):
        try:
            connections.connect(
                alias=self.config.milvus_alias,
                host=self.config.milvus_host,
                port=self.config.milvus_port,
            )
            self._connected = True
            logger.info(
                f"Connected to Milvus at "
                f"{self.config.milvus_host}:{self.config.milvus_port}"
            )
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Connection attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Milvus after {max_retries} attempts: {e}")
                raise
```

#### Fix 3: Load collection once during initialization
```python
# src/retrieval/rag_pipeline.py - create_collection()
def create_collection(self):
    # ... existing code ...
    self._collection.load()  # Load once after creation
    logger.info(f"Loaded collection: {self.config.collection_name}")
```

Then remove the redundant `load()` call from `search()`:
```python
def search(self, query: str, ...):
    if not self._collection:
        self.create_collection()
    
    # Remove: self._collection.load()  # Already loaded
```

---

### 5. **Steps Taken** (调查步骤)

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `rag_pipeline.py` source code | Connection logic at lines 155-170, no timeout/retry |
| 2 | Read `docker-compose.yml` | Port mapping 19531:19530 with explicit warning comment |
| 3 | Read `rag_config.yaml` | Port set to 19530 with `# BUG: Docker uses 19531` comment |
| 4 | Read `test_rag_pipeline.py` | Tests confirm no timeout field exists; mocks hide real issues |
| 5 | Verified BGE embedding dimension via web search | Confirmed 1024 dimensions (HuggingFace, ModelScope) |
| 6 | Searched pymilvus documentation | `connections.connect()` accepts: `alias`, `host`, `port`, `uri`, `secure` — no `timeout` |
| 7 | Analyzed `index_corpus.py` usage pattern | Confirms typical usage flow |
| 8 | Checked `__init__.py` exports | Standard module structure |

---

### 6. **Tools Used** (使用工具)

| Tool | Purpose |
|------|---------|
| `Read` | Read all source files (rag_pipeline.py, docker-compose.yml, rag_config.yaml, tests) |
| `Grep` | Search for embedding_dim, timeout, retry patterns across codebase |
| `WebSearch` | Verify BGE embedding dimensions, pymilvus API parameters |
| `WebFetch` | Fetch official pymilvus documentation for `connections.connect()` |

---

### 7. **Verification** (验证)

| Finding | Verification Method | Status |
|---------|--------------------|--------|
| Port mismatch | Compared `docker-compose.yml:45` vs `rag_config.yaml:6` | ✅ Confirmed |
| No timeout support | Fetched official pymilvus docs | ✅ Confirmed |
| Embedding dim = 1024 | Web search (HuggingFace discussion, ModelScope) | ✅ Confirmed |
| load() called per search | Test assertion at `test_rag_pipeline.py:91` | ✅ Confirmed |
| BUG comment ignored | Direct read of `rag_config.yaml:6` | ✅ Confirmed |

---

### Summary

The **"Connection refused"** error is caused by a **port mismatch**: Docker exposes Milvus on host port **19531**, but the RAG config tries to connect to **19530**. This was explicitly documented in comments but never fixed.

The **vector dimensions are correct** (1024 for BGE-large-zh-v1.5) — this is NOT the issue.

Additional technical debt includes: no connection timeout, no retry logic, inefficient collection loading on every search, and silent exception handling that could leave the system in an inconsistent state.
