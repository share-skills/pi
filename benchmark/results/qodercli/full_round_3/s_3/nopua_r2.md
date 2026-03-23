# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 115.07s

---

## Investigation Summary: RAG Pipeline Milvus Connection Issue

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Port mismatch causing "Connection refused"** | P0 - Critical | `docker-compose.yml:45`, `rag_config.yaml:6` |
| **2** | **Unused imports in rag_pipeline.py** | P3 - Minor | `rag_pipeline.py:22-23` |
| **3** | **Missing connection retry/timeout logic** | P2 - Medium | `rag_pipeline.py:155-170` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **H1** | **Unused `os` and `time` imports** - Code quality issue | Minor | `rag_pipeline.py:22-23` |
| **H2** | **No connection validation before operations** - `search()` and `index_chunks()` assume collection exists without checking connection state | Medium | `rag_pipeline.py:286-300` |
| **H3** | **Collection load called on every search** - Performance issue, `load()` is expensive and should be cached | Medium | `rag_pipeline.py:303` |
| **H4** | **Unused `Tuple` import** from typing | Minor | `rag_pipeline.py:25` |
| **H5** | **No graceful degradation when Milvus is unavailable** - Constructor fails immediately without retry | Medium | `rag_pipeline.py:152-153` |

---

### 3. Root Cause

**Primary Root Cause:** Docker port mapping mismatch

The `docker-compose.yml` exposes Milvus on **host port 19531** but maps to **container port 19530**:
```yaml
ports:
  - "19531:19530"   # Host:Container
```

However, both the code (`RAGConfig` default) and config file (`rag_config.yaml`) use **port 19530**:
```python
# rag_pipeline.py:49
milvus_host: str = "localhost"
milvus_port: int = 19530  # ❌ Should be 19531 for Docker
```

When the Python code connects to `localhost:19530`, nothing is listening there because Docker exposed Milvus on port 19531.

**Vector Dimension:** ✅ **VERIFIED CORRECT** - BGE-large-zh-v1.5 uses **1024 dimensions**, which matches the code (`BGE_EMBEDDING_DIM = 1024`).

---

### 4. Recommended Fix

#### Option A: Fix the config (Recommended - No code change)

Update `configs/rag_config.yaml`:
```yaml
milvus_port: 19531   # Changed from 19530 to match Docker host port
```

#### Option B: Fix the Docker mapping (Alternative)

Update `docker-compose.yml`:
```yaml
ports:
  - "19530:19530"   # Use standard port on host
```

#### Additional Fixes for Hidden Issues:

1. **Remove unused imports** (`rag_pipeline.py`):
```python
# Remove these lines:
import os
import time
# Also remove 'Tuple' from typing import if unused
```

2. **Add connection retry logic** (`_connect` method):
```python
def _connect(self, max_retries: int = 3, retry_delay: float = 1.0):
    """Establish connection to Milvus with retry."""
    for attempt in range(max_retries):
        try:
            connections.connect(...)
            self._connected = True
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay)
```

3. **Cache collection load state** to avoid calling `load()` on every search.

---

### 5. Steps Taken

1. **Read `rag_pipeline.py`** - Analyzed connection logic, embedding dimension constant, and collection setup
2. **Read `docker-compose.yml`** - Discovered port mismatch (19531:19530)
3. **Read `rag_config.yaml`** - Confirmed config uses wrong port (19530)
4. **Verified BGE embedding dimension** via web search - Confirmed 1024 is correct for BAAI/bge-large-zh-v1.5
5. **Read test files** - Understood expected behavior and test coverage
6. **Searched for related issues** - Checked for similar patterns across codebase

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (rag_pipeline.py, docker-compose.yml, rag_config.yaml, tests) |
| `Glob` | Locate configuration and test files |
| `Grep` | Search for import statements and dimension references |
| `WebSearch` | Verify BGE-large-zh-v1.5 embedding dimension |

---

### 7. Verification

**Findings Verified:**
- ✅ Port mismatch confirmed: `docker-compose.yml:45` shows `"19531:19530"` mapping
- ✅ Config uses wrong port: `rag_config.yaml:6` has `milvus_port: 19530`
- ✅ Embedding dimension correct: Web search confirms BGE-large-zh-v1.5 = 1024 dimensions
- ✅ Unused imports confirmed: `os` and `time` imported but never referenced in code logic

**Not Verified (would require running environment):**
- ❌ Cannot run actual connection test (no Milvus instance available)
- ❌ Cannot run build/tests (missing dependencies in current environment)

---

### Quick Fix Command

To fix the primary issue immediately:

```bash
# Edit configs/rag_config.yaml
sed -i 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml
```

Or if running from Python directly:

```python
config = RAGConfig(milvus_port=19531)  # Override default
```
