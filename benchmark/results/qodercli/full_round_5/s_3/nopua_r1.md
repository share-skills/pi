# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 81.9s

---

Now I have all the information I need. Let me compile my findings:

## Investigation Summary: RAG Pipeline Milvus Connection Timeout

### 1. Issues Found

**Primary Issue - Port Mismatch (Critical)**
- **Location**: `docker-compose.yml:45` and `configs/rag_config.yaml:6`
- **Problem**: Docker Compose maps host port `19531` to container port `19530`, but `rag_config.yaml` specifies `milvus_port: 19530`
- **Evidence from docker-compose.yml**:
  ```yaml
  ports:
    # NOTE: Host port is 19531 but container port is 19530.
    # The RAG config defaults to 19530 — this WILL cause connection failures.
    # Fix: set milvus_port: 19531 in rag_config.yaml
    - "19531:19530"   # <-- Intentional port mismatch for Scenario 3
  ```
- **Evidence from rag_config.yaml**:
  ```yaml
  milvus_port: 19530   # BUG: Docker uses 19531
  ```

**Secondary Issue - No Connection Timeout Configuration**
- **Location**: `src/retrieval/rag_pipeline.py:155-170` (`_connect` method)
- **Problem**: The `connections.connect()` call does not specify a `timeout` parameter, defaulting to 10 seconds. This can cause premature failures in slow environments.
- **Test confirms missing field**: `tests/test_rag_pipeline.py:19-22` explicitly tests that there is NO `connection_timeout` field

### 2. Hidden Issues Discovered

**Issue A - Collection Load Called on Every Search (Performance)**
- **Location**: `src/retrieval/rag_pipeline.py:303`
- **Problem**: `self._collection.load()` is called on every `search()` call, which is inefficient
- **Test confirms**: `tests/test_rag_pipeline.py:73-91` verifies `load()` is called 3 times for 3 searches

**Issue B - Embedding Dimension Hardcoded Without Validation**
- **Location**: `src/retrieval/rag_pipeline.py:42` and line 55
- **Problem**: `BGE_EMBEDDING_DIM = 1024` is hardcoded. If the actual model returns different dimensions, there will be schema mismatches with no validation at runtime.

**Issue C - Auto-flush May Cause Performance Issues**
- **Location**: `src/retrieval/rag_pipeline.py:272-274`
- **Problem**: `auto_flush` is enabled by default with `flush_interval: 1000`. For large indexing jobs, frequent flushes can significantly slow down performance.

### 3. Root Cause

The **"Connection refused"** error occurs because:

1. Milvus Docker container exposes port `19530` internally
2. Docker Compose maps this to host port `19531` (not `19530`)
3. The RAG pipeline tries to connect to `localhost:19530`
4. Nothing is listening on port `19530` → Connection refused

The embedder working standalone confirms this is NOT an embedding model issue—it's purely a network configuration problem.

### 4. Recommended Fix

**Fix 1: Update rag_config.yaml (Primary)**
```yaml
# configs/rag_config.yaml
milvus_port: 19531   # Changed from 19530 to match Docker mapping
```

**Fix 2: Add Connection Timeout (Recommended)**
```python
# src/retrieval/rag_pipeline.py:155-170
def _connect(self):
    """Establish connection to Milvus."""
    try:
        connections.connect(
            alias=self.config.milvus_alias,
            host=self.config.milvus_host,
            port=self.config.milvus_port,
            timeout=30,  # Add explicit timeout (default is 10s)
        )
        self._connected = True
        # ... rest unchanged
```

**Fix 3: Optional - Cache Collection Load State**
```python
# Add a flag to track if collection is already loaded
self._collection_loaded = False

# In search(), only load if not already loaded:
if not self._collection_loaded:
    self._collection.load()
    self._collection_loaded = True
```

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `rag_pipeline.py` | Understood connection logic |
| 2 | Read `docker-compose.yml` | Found port mismatch comment |
| 3 | Read `rag_config.yaml` | Confirmed incorrect port config |
| 4 | Read `test_rag_pipeline.py` | Verified test coverage gaps |
| 5 | Read `pymilvus/orm/connections.py` | Understood timeout defaults |
| 6 | Cross-referenced all files | Identified root cause |

### 6. Tools Used

- **Read tool**: Examined 7 source files
- **Glob tool**: Located configuration and test files
- **Grep tool**: Searched pymilvus API documentation

### 7. Verification

**Verified Findings:**
- ✅ Docker port mapping confirmed: `"19531:19530"` in docker-compose.yml line 45
- ✅ Config port confirmed: `milvus_port: 19530` in rag_config.yaml line 6
- ✅ Both files have explicit comments noting this is an intentional bug for "Scenario 3"
- ✅ pymilvus `connections.connect()` defaults to 10s timeout (no timeout param in code)
- ✅ Test file explicitly checks for absence of `connection_timeout` field

**To Verify Fix:**
```bash
# After updating rag_config.yaml:
python scripts/index_corpus.py --chunks ./data/chunks --config configs/rag_config.yaml
```

---

**Summary**: This is a classic Docker port mapping misconfiguration. The fix is straightforward—change `milvus_port` from `19530` to `19531` in `configs/rag_config.yaml`. The intentional comments in both files suggest this was designed as a test scenario for debugging skills.
