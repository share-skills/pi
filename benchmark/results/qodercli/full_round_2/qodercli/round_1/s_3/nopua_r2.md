# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 82.36s

---

Now I have all the information I need. Let me compile my findings:

---

## Investigation Summary: RAG Pipeline Milvus Connection Timeout

### 1. Issues Found

**Primary Issue - Port Mismatch:**
- **Location**: `docker-compose.yml:42-45`, `rag_pipeline.py:50`, `rag_config.yaml:6`
- **Problem**: Docker Compose maps host port `19531` to container port `19530`, but:
  - `RAGConfig` defaults to `milvus_port: int = 19530` (line 50 in `rag_pipeline.py`)
  - `rag_config.yaml` explicitly sets `milvus_port: 19530` with a comment `# BUG: Docker uses 19531`
- **Result**: When running via Docker, connection attempts to `localhost:19530` fail because the actual exposed port is `19531`

**Evidence from docker-compose.yml (lines 42-45):**
```yaml
ports:
  # NOTE: Host port is 19531 but container port is 19530.
  # The RAG config defaults to 19530 — this WILL cause connection failures.
  # Fix: set milvus_port: 19531 in rag_config.yaml
  - "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

### 2. Hidden Issues Discovered

**Issue A - Missing Connection Timeout Configuration:**
- `RAGConfig` has no `connection_timeout` field
- The `_connect()` method doesn't handle timeout scenarios gracefully
- If Milvus is slow to respond, the connection attempt could hang indefinitely

**Issue B - No Retry Logic:**
- Connection is attempted once in `__init__` via `_connect()`
- No retry mechanism for transient network issues or Milvus startup delays
- Docker containers may take time to become ready; immediate connection attempts will fail

**Issue C - Embedding Dimension Mismatch Risk:**
- `BGE_EMBEDDING_DIM = 1024` is hardcoded
- If user changes embedding model without updating `embedding_dim`, schema creation will fail
- No validation that the embedding model's actual output dimension matches `config.embedding_dim`

**Issue D - Collection Load Called on Every Search:**
- `search()` method calls `self._collection.load()` on every invocation (line 303)
- This is inefficient; collection should be loaded once after indexing
- Test file confirms this behavior: `test_search_calls_load` verifies load is called 3 times for 3 searches

**Issue E - AutoID Primary Key Without ID Tracking:**
- Schema uses `auto_id=True` for primary key (line 194)
- No mechanism to track inserted IDs for updates/deletions
- Makes it impossible to update specific chunks without recreating the collection

### 3. Root Cause

**Fundamental Cause:** Docker port mapping configuration mismatch combined with hardcoded default values in the codebase.

The docker-compose.yml intentionally exposes Milvus on host port `19531` while the container listens on `19530`. However, both the Python code (`RAGConfig.milvus_port` default) and YAML config (`rag_config.yaml`) use `19530`, causing connection refused errors when accessing via Docker.

### 4. Recommended Fix

**Immediate Fix (Port Mismatch):**
```python
# Option 1: Update rag_config.yaml
rag:
  milvus_port: 19531  # Changed from 19530 to match Docker host port
```

**OR**

```python
# Option 2: Update docker-compose.yml to use matching ports
ports:
  - "19530:19530"  # Use same port on host and container
```

**Additional Improvements:**
1. Add `connection_timeout` parameter to `RAGConfig` with sensible default (e.g., 30 seconds)
2. Implement retry logic with exponential backoff in `_connect()`
3. Validate embedding dimension matches model output before collection creation
4. Cache collection loaded state to avoid redundant `load()` calls
5. Consider using explicit IDs instead of auto_id for better chunk management

### 5. Steps Taken

1. **Read docker-compose.yml** - Discovered port mapping `19531:19530` with explicit warning comments
2. **Read rag_pipeline.py** - Confirmed default port `19530` in `RAGConfig` dataclass
3. **Read rag_config.yaml** - Found explicit `milvus_port: 19530` with bug comment
4. **Read test_rag_pipeline.py** - Verified tests mock Milvus connection, wouldn't catch this issue
5. **Searched for milvus references** - Confirmed consistent use of port 19530 throughout codebase

### 6. Tools Used

- `Read` - Read source files (rag_pipeline.py, docker-compose.yml, rag_config.yaml, test_rag_pipeline.py, verify_issues.py)
- `Glob` - Searched for YAML configuration files
- `Grep` - Searched for all milvus-related references across the project

### 7. Verification

**Verified Findings:**
- ✅ Docker compose port mapping confirmed: `"19531:19530"` (line 45, docker-compose.yml)
- ✅ Code default port confirmed: `milvus_port: int = 19530` (line 50, rag_pipeline.py)
- ✅ Config file port confirmed: `milvus_port: 19530` (line 6, rag_config.yaml)
- ✅ Bug documented in config: `# BUG: Docker uses 19531` comment present
- ✅ Warning in docker-compose: Explicit comment warns about connection failure

**Test Evidence:**
The test suite mocks Milvus connections (`@patch("src.retrieval.rag_pipeline.connections")`), so these integration issues would not be caught by automated tests.
