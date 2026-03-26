# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 134.67s

---

## Investigation Complete — Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Port mismatch: Docker exposes 19531, code connects to 19530** | Critical | `docker-compose.yml:45`, `rag_pipeline.py:49-50`, `rag_config.yaml:6` |
| 2 | **No connection timeout configured** | Medium | `rag_pipeline.py:155-170` |
| 3 | **No retry mechanism for transient connection failures** | Medium | `rag_pipeline.py:155-170` |
| 4 | **Collection creation lacks proper error handling** | Low | `rag_pipeline.py:227-231` |

### 2. Hidden Issues Beyond the Ask

| # | Issue | Impact | Evidence |
|---|-------|--------|----------|
| 1 | **`collection.load()` called on every search** — Performance issue | High | `test_rag_pipeline.py:91` confirms `load()` called 3 times for 3 searches |
| 2 | **`source` field max_length=512 may truncate long paths** | Low | `rag_pipeline.py:198` |
| 3 | **Auto-flush every 1000 chunks may cause memory buildup** | Medium | `rag_config.yaml:29-30` |
| 4 | **No Milvus health check before connection attempt** | Medium | `_connect()` directly calls `connections.connect()` without preflight |
| 5 | **Embedding model loads synchronously in constructor** — Slow startup | Low | `rag_pipeline.py:152-153` |

### 3. Root Cause

**Primary Root Cause:** The Docker Compose file explicitly maps host port 19531 to container port 19530 (line 45), but both `RAGConfig` defaults (`rag_pipeline.py:49-50`) and `rag_config.yaml` (line 6) use port 19530. This causes "Connection refused" because nothing is listening on port 19530.

The docker-compose.yml even contains an explicit warning comment:
```yaml
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
- "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

### 4. Recommended Fix

#### Immediate Fix (Port Mismatch)

**Option A: Change config to match Docker** (Recommended)
```python
# rag_pipeline.py or rag_config.yaml
milvus_port: int = 19531  # Changed from 19530
```

**Option B: Change Docker to match config**
```yaml
# docker-compose.yml
- "19530:19530"  # Changed from 19531:19530
```

#### Additional Fixes

```python
# 1. Add timeout and retry to _connect()
def _connect(self, max_retries: int = 3, timeout: float = 30.0):
    for attempt in range(max_retries):
        try:
            connections.connect(
                alias=self.config.milvus_alias,
                host=self.config.milvus_host,
                port=self.config.milvus_port,
                timeout=timeout,  # pymilvus supports this parameter
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

# 2. Cache collection load state
def __init__(self, ...):
    self._collection_loaded = False  # Track load state

def search(self, ...):
    if not self._collection_loaded:
        self._collection.load()
        self._collection_loaded = True
```

### 5. Steps Taken

1. **Read source files** — Analyzed `rag_pipeline.py`, `docker-compose.yml`, `rag_config.yaml`, and `test_rag_pipeline.py`
2. **Checked pymilvus source** — Read `connections.py` to understand available connection parameters (timeout, retry support)
3. **Verified embedding dimension** — Confirmed BGE-large-zh-v1.5 uses 1024 dimensions (matches code)
4. **Analyzed test file** — Found performance issue with repeated `collection.load()` calls
5. **Cross-referenced configs** — Identified port mismatch between Docker and application configs

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (rag_pipeline.py, docker-compose.yml, configs, tests) |
| `Grep` | Search for timeout/retry patterns, connection parameters |
| `Glob` | Find related configuration and test files |
| `WebSearch` | Verify BGE embedding dimension specifications |
| `TodoWrite` | Track investigation progress |

### 7. Verification

**Verified findings:**
- ✅ Port mismatch confirmed: `docker-compose.yml:45` explicitly shows `19531:19530`
- ✅ Config defaults to 19530: `rag_pipeline.py:49-50`, `rag_config.yaml:6`
- ✅ Embedding dimension correct: 1024 matches BGE-large-zh-v1.5 specification
- ✅ pymilvus `connect()` supports `timeout` parameter (line 298 in connections.py)
- ✅ Test confirms `load()` called on every search (test_rag_pipeline.py:91)

**Not verified (would require running environment):**
- ❌ Actual Milvus container status (Docker daemon not accessible in current environment)
- ❌ Live connection test with corrected port

---

**Summary:** The "Connection refused" error is caused by a port mismatch. Docker exposes Milvus on host port 19531, but the RAG pipeline tries to connect to 19530. Fix: Change `milvus_port` to 19531 in your config. Additionally, implement timeout/retry logic and cache collection load state for better resilience and performance.
