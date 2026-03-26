# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 1
## Duration: 143.08s

---

## Investigation Complete

Based on my thorough analysis of the RAG pipeline code and configuration files, here are my findings:

---

## 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Port mismatch: Docker exposes 19531, config defaults to 19530** | `docker-compose.yml:L45`, `rag_config.yaml:L6`, `rag_pipeline.py:L50` | 🔴 Blocker |
| 2 | **BGE embedding dimension is CORRECT (1024)** - Not a bug | `rag_pipeline.py:L42` | ✅ Verified OK |
| 3 | **No connection timeout configuration** - Can cause indefinite hangs | `RAGConfig` dataclass missing `connection_timeout` field | 🟡 Suggestion |
| 4 | **Unused import: `os` and `time`** | `rag_pipeline.py:L22-L23` | ⚪ Nit |
| 5 | **Unused import: `Tuple`** | `rag_pipeline.py:L25` | ⚪ Nit |

---

## 2. Hidden Issues

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 1 | **`collection.load()` called on EVERY search** - Performance issue, should cache loaded state | `rag_pipeline.py:L303` | ⚡ Performance |
| 2 | **Silent exception swallowing in `create_collection()`** - Falls through without re-raising | `rag_pipeline.py:L227-L231` | 🔒 Correctness |
| 3 | **No retry logic for transient connection failures** | `_connect()` method `rag_pipeline.py:L155-L170` | 🔒 Reliability |
| 4 | **Hardcoded Milvus alias "default"** - No multi-tenant support | `rag_pipeline.py:L51` | 📖 Limitation |
| 5 | **Missing chunk_index validation** - `i + j` calculation incorrect | `rag_pipeline.py:L255` | ✅ Correctness |
| 6 | **Empty embeddings array returns `np.array([])` without shape info** - Can break downstream code | `rag_pipeline.py:L110-L111` | ⚠️ Edge case |
| 7 | **No health check before connection attempt** | `_connect()` method | 🔒 Reliability |

---

## 3. Root Cause

**Primary Root Cause:** The Docker Compose file intentionally maps host port **19531** to container port **19530** (see `docker-compose.yml:L45`), but:
- `rag_config.yaml` defaults to **19530** (line 6)
- `RAGConfig` dataclass defaults to **19530** (line 50)
- Comment in `docker-compose.yml` explicitly warns about this mismatch

The error message states:
```yaml
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
```

**Vector Dimensions:** ✅ **VERIFIED MATCH** - BGE-large-zh-v1.5 uses 1024 dimensions, which matches `BGE_EMBEDDING_DIM = 1024` in the code.

---

## 4. Recommended Fix

### Fix 1: Update `rag_config.yaml` (Immediate fix)

```yaml
# Before (line 6):
milvus_port: 19530   # BUG: Docker uses 19531

# After:
milvus_port: 19531   # Fixed: Match Docker host port
```

### Fix 2: Add connection timeout to `RAGConfig` (Reliability improvement)

```python
# In RAGConfig dataclass, add:
milvus_connection_timeout: int = 30  # seconds
```

### Fix 3: Remove unused imports

```python
# Remove from rag_pipeline.py:L22-L23,L25:
import os
import time
from typing import ..., Tuple, ...
```

### Fix 4: Fix chunk_index calculation bug

```python
# Before (rag_pipeline.py:L255):
indices = [c.get("chunk_index", i + j) for j, c in enumerate(batch)]

# After:
indices = [c.get("chunk_index", i + j) for j, _ in enumerate(batch)]
# Or better: track global index separately
```

---

## 5. Steps Taken

1. **Read source files**: Located and read both copies of `rag_pipeline.py` (identical)
2. **Read Docker configuration**: Analyzed `docker-compose.yml` - discovered intentional port mismatch
3. **Read config files**: Analyzed `rag_config.yaml` - confirmed default port is wrong
4. **Searched for test files**: Found and read `test_rag_pipeline.py` to understand expected behavior
5. **Searched for usage patterns**: Read `index_corpus.py` to see how RAGPipeline is instantiated
6. **Verified embedding dimension**: Web search confirmed BGE-large-zh-v1.5 uses 1024 dimensions
7. **Attempted Docker verification**: Docker daemon not running on current system
8. **Code review**: Performed line-by-line analysis for hidden issues (unused imports, edge cases, performance)

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files, configs, tests |
| `Glob` | Locate related files (docker-compose, configs, tests) |
| `Grep` | Search for embedding dimension references, usage patterns |
| `WebSearch` | Verify BGE-large-zh-v1.5 embedding dimension |
| `Bash` | Check Docker container status |

---

## 7. Verification

**Verification Commands:**

```bash
# 1. Verify the fix works - update config and test connection:
cd benchmark/data/test-project
# Edit configs/rag_config.yaml, change milvus_port: 19531

# 2. Test Milvus connection (if Docker is running):
docker ps | grep milvus
curl http://localhost:19531/v1/vector/collections 2>/dev/null || echo "Milvus HTTP API check"

# 3. Run the pipeline test:
python scripts/index_corpus.py --chunks ./data/chunks --config configs/rag_config.yaml

# 4. Verify embedding dimension matches:
python3 -c "
from src.retrieval.rag_pipeline import BGE_EMBEDDING_DIM
print(f'Configured embedding dim: {BGE_EMBEDDING_DIM}')
# Should output: 1024
"
```

**Expected outcome after fix:**
- Connection to Milvus succeeds when using port 19531
- Vector dimensions match (1024 = 1024) ✅
- No more "Connection refused" errors

---

### Summary

| Aspect | Status |
|--------|--------|
| **Root cause identified** | ✅ Port mismatch (19530 vs 19531) |
| **Vector dimensions verified** | ✅ 1024 matches BGE-large-zh-v1.5 |
| **Hidden issues found** | ✅ 7 additional issues beyond the ask |
| **Fix provided** | ✅ Update `milvus_port: 19531` in config |
