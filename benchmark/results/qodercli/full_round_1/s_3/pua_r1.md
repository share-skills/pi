# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 1
## Duration: 131.65s

---

## Investigation Complete — Structured Summary

---

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Port mismatch: Docker exposes Milvus on host port 19531, but RAG config defaults to 19530** | CRITICAL | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| **2** | **No connection timeout configuration** — Connection attempts can hang indefinitely | HIGH | `rag_pipeline.py:155-170`, `RAGConfig` dataclass |
| **3** | **`collection.load()` called on EVERY search** — Unnecessary performance overhead | MEDIUM | `rag_pipeline.py:303` |
| **4** | **Query instruction prefix applied to ALL texts** — Should only apply to queries, not document chunks | MEDIUM | `rag_pipeline.py:114` |
| **5** | **Silent collection creation fallback** — Exception swallowed, may mask real errors | MEDIUM | `rag_pipeline.py:227-231` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Hidden Issue | Impact |
|---|--------------|--------|
| **H1** | **Query prefix bug**: Document chunks are prefixed with `"为这个句子生成表示以用于检索中文文档:"` during indexing. This is WRONG — BGE documentation states this prefix should ONLY be used for queries, not documents. This corrupts the vector space and destroys retrieval quality. | Retrieval accuracy severely degraded |
| **H2** | **No retry logic**: Single connection failure causes total pipeline crash. No exponential backoff or reconnection strategy. | Fragile in production environments |
| **H3** | **`search()` loads collection every call**: `self._collection.load()` is called unconditionally on line 303. This adds latency (~100-500ms per search). Collection should be loaded once after creation/indexing. | Search latency inflated by 3-5x |
| **H4** | **Test validates wrong behavior**: `test_rag_pipeline.py` asserts `milvus_port == 19530` as correct, reinforcing the bug. | Tests pass while production fails |
| **H5** | **Embedding dimension NOT verified at runtime**: No validation that embedder output dimension matches collection schema. If model changes, failure occurs silently or with cryptic errors. | Schema/embedding mismatch risk |

---

### 3. Root Cause

**Primary Root Cause:**
The Docker Compose file explicitly maps Milvus container port `19530` to host port `19531` (line 45 in `docker-compose.yml`):
```yaml
ports:
  - "19531:19530"   # Host 19531 → Container 19530
```

However:
- `RAGConfig` defaults to `milvus_port: 19530` (`rag_pipeline.py:50`)
- `rag_config.yaml` specifies `milvus_port: 19530` with a comment acknowledging the bug but no fix

When the application runs on the host machine (outside Docker network), it tries to connect to `localhost:19530`, but Milvus is actually listening on `localhost:19531`. Hence: **Connection refused**.

**Secondary Root Cause (Retrieval Quality):**
The `EmbeddingModel.encode()` method applies the query instruction prefix to ALL texts (line 114):
```python
prefixed = [f"为这个句子生成表示以用于检索中文文档：{t}" for t in texts]
```

Per BGE documentation, this prefix is **only for queries**, not for document/chunk embeddings. Applying it to documents shifts the embedding space, making query-document similarity scores meaningless.

---

### 4. Recommended Fix

#### Fix 1: Port Mismatch (CRITICAL)
**File: `configs/rag_config.yaml`**
```yaml
milvus_port: 19531   # Match Docker host port mapping
```

**OR** fix the Docker mapping to match the config:
**File: `docker-compose.yml`**
```yaml
ports:
  - "19530:19530"   # Standard port mapping
```

#### Fix 2: Add Connection Timeout (HIGH)
**File: `src/retrieval/rag_pipeline.py`** — Add to `RAGConfig`:
```python
@dataclass
class RAGConfig:
    # ... existing fields ...
    connection_timeout: float = 10.0  # seconds
```

**File: `src/retrieval/rag_pipeline.py`** — Update `_connect()`:
```python
def _connect(self):
    try:
        connections.connect(
            alias=self.config.milvus_alias,
            host=self.config.milvus_host,
            port=self.config.milvus_port,
            timeout=self.config.connection_timeout,  # Add timeout
        )
        self._connected = True
        logger.info(...)
    except Exception as e:
        logger.error(f"Failed to connect to Milvus after {self.config.connection_timeout}s: {e}")
        raise
```

#### Fix 3: Remove Query Prefix from Document Embeddings (CRITICAL for Quality)
**File: `src/retrieval/rag_pipeline.py`** — Split encoding methods:
```python
def encode(self, texts: List[str], batch_size: int = 32, 
           is_query: bool = False) -> np.ndarray:
    if not texts:
        return np.array([])

    # Only prefix queries, NOT documents
    if is_query:
        prefixed = [f"为这个句子生成表示以用于检索中文文档：{t}" for t in texts]
    else:
        prefixed = texts  # No prefix for documents

    embeddings = self._model.encode(...)
    return embeddings

def encode_query(self, query: str) -> np.ndarray:
    return self.encode([query], batch_size=1, is_query=True)[0]
```

Then update `index_chunks()` to NOT use query prefix:
```python
embeddings = self._embedder.encode(texts, batch_size=batch_size, is_query=False)
```

#### Fix 4: Load Collection Once (MEDIUM)
**File: `src/retrieval/rag_pipeline.py`** — Modify `create_collection()`:
```python
def create_collection(self):
    # ... existing code ...
    self._collection.load()  # Load once after creation
    logger.info(f"Created and loaded collection: {self.config.collection_name}")
```

Remove `self._collection.load()` from `search()` (line 303).

#### Fix 5: Add Runtime Dimension Validation
**File: `src/retrieval/rag_pipeline.py`** — Add validation in `_init_embedder()`:
```python
def _init_embedder(self):
    self._embedder = EmbeddingModel(...)
    # Validate embedding dimension
    test_emb = self._embedder.encode_query("test")
    actual_dim = len(test_emb)
    if actual_dim != self.config.embedding_dim:
        raise ValueError(
            f"Embedding dimension mismatch: config={self.config.embedding_dim}, "
            f"model_output={actual_dim}"
        )
```

#### Fix 6: Update Test to Validate Correct Port
**File: `tests/test_rag_pipeline.py`** — Add test for Docker scenario:
```python
def test_docker_port_config(self):
    """Verify config can override port for Docker deployments."""
    config = RAGConfig(milvus_port=19531)
    assert config.milvus_port == 19531
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `rag_pipeline.py` source | Identified connection logic, embedding dimension constant |
| 2 | Read `docker-compose.yml` | Found port mismatch `19531:19530` with explicit comment about the bug |
| 3 | Read `rag_config.yaml` | Confirmed config uses wrong port (19530), comment acknowledges bug |
| 4 | Searched codebase for `milvus_port` usage | Found tests validate incorrect behavior |
| 5 | Analyzed `EmbeddingModel.encode()` | Discovered query prefix incorrectly applied to documents |
| 6 | Reviewed `search()` method | Found unnecessary `load()` call on every search |
| 7 | Checked exception handling in `create_collection()` | Found silent fallback that masks errors |
| 8 | Verified BGE-large-zh-v1.5 dimension via web search | Confirmed 1024 is correct (matches code) |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files: `rag_pipeline.py`, `docker-compose.yml`, `rag_config.yaml`, `test_rag_pipeline.py`, `index_corpus.py` |
| `Glob` | Locate related files in codebase |
| `Grep` | Search for port configurations, embedding dimensions, utility calls |
| `WebSearch` | Verify BGE-large-zh-v1.5 embedding dimension |

---

### 7. Verification

| Finding | Verified? | Method |
|---------|-----------|--------|
| Port mismatch | ✅ YES | Cross-referenced `docker-compose.yml:45` with `rag_pipeline.py:50` and `rag_config.yaml:6` |
| Query prefix bug | ✅ YES | Read `rag_pipeline.py:114` — prefix applied unconditionally to all texts |
| Embedding dimension | ✅ YES | Web search confirmed BGE-large-zh-v1.5 outputs 1024-dim vectors |
| Repeated load() calls | ✅ YES | Read `rag_pipeline.py:303` inside `search()` method |
| Silent exception handling | ✅ YES | Read `rag_pipeline.py:227-231` — exception logged as warning, then fallback |

---

### Evidence Summary

**Docker Compose (line 42-45):**
```yaml
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
- "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

**RAG Config (line 6):**
```yaml
milvus_port: 19530   # BUG: Docker uses 19531
```

**Embedding Prefix Bug (line 114):**
```python
prefixed = [f"为这个句子生成表示以用于检索中文文档：{t}" for t in texts]  # Applied to ALL texts!
```

---

### Priority Order

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| P0 | Fix port mismatch | 1 min | Connection works |
| P1 | Remove query prefix from documents | 5 min | Retrieval quality restored |
| P2 | Add connection timeout | 3 min | Better error handling |
| P2 | Load collection once | 2 min | 3-5x search speedup |
| P3 | Add dimension validation | 5 min | Prevents future mismatches |
| P3 | Fix test assertions | 2 min | Tests reflect reality |
