# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 1
## Duration: 72.75s

---

## Investigation Complete

---

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Port mismatch: RAG pipeline connects to 19530, but Docker exposes Milvus on host port 19531** | P0 - Critical | `docker-compose.yml:45`, `rag_pipeline.py:50`, `rag_config.yaml:6` |
| 2 | **No connection retry logic or timeout handling** | P2 - Medium | `rag_pipeline.py:155-170` |

---

### 2. Hidden Issues

| # | Issue | Impact |
|---|-------|--------|
| 1 | **Collection load() called on every search** - Inefficient, should cache loaded state | Performance degradation |
| 2 | **No connection health check before operations** - Assumes connection is always alive | Runtime failures after idle periods |
| 3 | **Test explicitly verifies 19530 port** - Test will pass but production fails (tests mock the connection) | False confidence in tests |
| 4 | **Comment in docker-compose.yml warns about this exact issue** - The bug was intentionally left as a trap | Documentation exists but ignored |

---

### 3. Root Cause

**The Docker Compose file maps Milvus container port 19530 to host port 19531:**
```yaml
ports:
  - "19531:19530"   # Host:Container mapping
```

However, both the code default and config file use port **19530**:
- `rag_pipeline.py:50`: `milvus_port: int = 19530`
- `rag_config.yaml:6`: `milvus_port: 19530   # BUG: Docker uses 19531`

When the RAGPipeline tries to connect to `localhost:19530`, nothing is listening there → **Connection refused**.

---

### 4. Recommended Fix

**Option A (Recommended): Change the config to match Docker**

Update `configs/rag_config.yaml`:
```yaml
milvus_port: 19531   # Fixed: Match Docker host port
```

Or update `src/retrieval/rag_pipeline.py` default:
```python
milvus_port: int = 19531  # Changed from 19530
```

**Option B: Change Docker to use standard port**

Update `docker-compose.yml:45`:
```yaml
ports:
  - "19530:19530"   # Use standard port
```

---

### 5. Steps Taken

1. **Read docker-compose.yml** - Discovered port mapping `19531:19530` with explicit comment warning about the mismatch
2. **Read rag_pipeline.py** - Confirmed default port is 19530
3. **Read rag_config.yaml** - Found explicit `# BUG: Docker uses 19531` comment
4. **Verified embedding dimension** - BGE-large-zh-v1.5 uses 1024 dimensions (confirmed via HuggingFace/ModelScope docs) - **dimensions match correctly**
5. **Read test file** - Tests mock connections so they pass regardless of actual port issues
6. **Read index_corpus.py** - Shows how the pipeline is used in production

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read docker-compose.yml, rag_pipeline.py, rag_config.yaml, test files |
| `Grep` | Search for embedding_dim references across codebase |
| `WebSearch` | Verify BGE-large-zh-v1.5 embedding dimension (1024 confirmed) |

---

### 7. Verification

**Verified findings:**
- ✅ Docker port mapping confirmed: `19531:19530` in `docker-compose.yml:45`
- ✅ Code default confirmed: `milvus_port: int = 19530` in `rag_pipeline.py:50`
- ✅ Config confirmed: `milvus_port: 19530` with bug comment in `rag_config.yaml:6`
- ✅ Embedding dimension verified: BGE-large-zh-v1.5 = 1024 dims (external sources confirm)
- ✅ Code dimension matches: `BGE_EMBEDDING_DIM = 1024` in `rag_pipeline.py:42`

**Evidence:** Direct file reads show the port mismatch. The docker-compose.yml even has an explicit comment on line 42-45:
```yaml
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
```

---

### Summary

The **"Connection refused"** error is caused by a **port mismatch**, not a network or authentication issue. The embedder dimension (1024) is correct and matches the collection schema. Fix the port in the config file from 19530 to 19531.
