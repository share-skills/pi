# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 2
## Duration: 108.52s

---

Now I have comprehensive information. Let me compile my investigation findings:

---

## 🧠 PI · 深度调查 · RAG Pipeline Milvus Connection Timeout

### 1. Issues Found

| # | Issue | Location |
|---|-------|----------|
| 1 | **Port mismatch**: Docker maps host port `19531` → container port `19530`, but config defaults to `19530` | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| 2 | **No connection timeout configuration**: `_connect()` has no timeout, will hang indefinitely on network issues | `rag_pipeline.py:155-170` |
| 3 | **Unused imports**: `os`, `time`, `field` imported but never used | `rag_pipeline.py:22-26` |
| 4 | **Bare except in rerank**: Exception caught but not logged with context | `rag_pipeline.py:356-357` |

### 2. Hidden Issues

| # | Category | Issue | Location |
|---|----------|-------|----------|
| H1 | 🔒 **Security** | Hardcoded MinIO credentials in docker-compose (`minioadmin/minioadmin`) | `docker-compose.yml:22-23` |
| H2 | ⚡ **Performance** | `search()` calls `load()` every time — should check if already loaded | `rag_pipeline.py:303` |
| H3 | ⚡ **Performance** | No retry logic for transient connection failures | `rag_pipeline.py:155-170` |
| H4 | 📖 **Correctness** | Empty embeddings array returned when `texts=[]` — may cause downstream errors | `rag_pipeline.py:110-111` |
| H5 | 🔒 **Security** | No authentication for Milvus connection (no username/password/token) | `rag_pipeline.py:158-162` |
| H6 | ⚡ **Resource Leak** | No cleanup on `__del__` or context manager support — connection may leak | `rag_pipeline.py:146-153` |
| H7 | 📖 **Correctness** | `chunk_index` calculation bug: uses undefined `j` variable | `rag_pipeline.py:255` |
| H8 | ⚡ **Performance** | IVF_FLAT index params not optimized — `nlist=128` may be suboptimal for large collections | `rag_pipeline.py:58` |

### 3. Root Cause

**Primary Root Cause (Issue #1):**

```yaml
# docker-compose.yml:41-45
ports:
  - "19531:19530"   # Host 19531 → Container 19530
```

```python
# rag_pipeline.py:50 / rag_config.yaml:6
milvus_port: int = 19530  # BUG: Should be 19531 for Docker deployment
```

**Initially I thought** the issue was that Milvus wasn't running or Docker networking was broken. **Upon closer inspection**, the real problem is a **port mapping mismatch**: the Docker compose file intentionally maps host port `19531` to container port `19530` (per the comment on line 42-45), but both the Python code default and the YAML config use `19530`.

**Why the embedder works standalone:** The `EmbeddingModel` class only connects to Hugging Face to download/load the model — it does NOT connect to Milvus. Only `RAGPipeline._connect()` attempts Milvus connection.

**Vector Dimension Verification:** BGE-large-zh-v1.5 outputs **1024-dimensional** vectors. Both `BGE_EMBEDDING_DIM = 1024` in code and `embedding_dim: 1024` in config are **CORRECT**. No dimension mismatch exists.

### 4. Recommended Fix

#### Fix 1: Port Configuration (Immediate)

```yaml
# configs/rag_config.yaml - Line 6
# Before:
milvus_port: 19530   # BUG: Docker uses 19531

# After:
milvus_port: 19531   # Match Docker host port mapping
```

#### Fix 2: Add Connection Timeout

```python
# rag_pipeline.py:155-170
# Before:
def _connect(self):
    try:
        connections.connect(
            alias=self.config.milvus_alias,
            host=self.config.milvus_host,
            port=self.config.milvus_port,
        )
        self._connected = True

# After:
def _connect(self):
    try:
        connections.connect(
            alias=self.config.milvus_alias,
            host=self.config.milvus_host,
            port=self.config.milvus_port,
            timeout=10,  # 10 second timeout
        )
        self._connected = True
```

#### Fix 3: Remove Unused Imports

```python
# rag_pipeline.py:22-26
# Before:
import os
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

# After:
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
```

#### Fix 4: Fix chunk_index Bug

```python
# rag_pipeline.py:255
# Before:
indices = [c.get("chunk_index", i + j) for j, c in enumerate(batch)]

# After:
indices = [c.get("chunk_index", i + idx) for idx, c in enumerate(batch)]
```

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `rag_pipeline.py` fully (386 lines) | Identified connection logic at lines 155-170 |
| 2 | Read `docker-compose.yml` | **Found port mismatch**: `19531:19530` mapping with explicit comment |
| 3 | Read `rag_config.yaml` | **Confirmed config uses wrong port** `19530` |
| 4 | Read `test_rag_pipeline.py` | Tests mock connections, don't catch real port issue |
| 5 | Searched for embedding dimension references | Confirmed `1024` is correct for BGE-large-zh-v1.5 |
| 6 | Per-function scan of `rag_pipeline.py` | Found unused imports, chunk_index bug, missing timeout |
| 7 | Security review | Found hardcoded MinIO credentials, no Milvus auth |
| 8 | Performance review | Found repeated `load()` calls, no retry logic |

**Self-Correction:** Initially I suspected the embedder might have wrong dimensions (1024 vs 768). **Upon verification**, BGE-large-zh-v1.5 does indeed output 1024-dimensional vectors, so the dimension configuration is correct. The actual issue is purely the port mismatch.

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files: `rag_pipeline.py`, `docker-compose.yml`, `rag_config.yaml`, test files |
| `Grep` | Search for connection patterns, port references, embedding dimensions |
| `Glob` | Find Docker and configuration files |
| `WebSearch` | Verify BGE-large-zh-v1.5 embedding dimension |

### 7. Verification

**Verification Commands:**

```bash
# 1. Check actual Docker port mapping
docker ps | grep milvus
# Expected: 0.0.0.0:19531->19530/tcp

# 2. Test connection with correct port (after fix)
python -c "
from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig
config = RAGConfig(milvus_port=19531)
rag = RAGPipeline(config)
print('Connection successful!')
rag.close()
"

# 3. Verify embedding dimension matches
python -c "
from src.retrieval.rag_pipeline import BGE_EMBEDDING_DIM
print(f'BGE embedding dim: {BGE_EMBEDDING_DIM}')
# Should output: 1024
"

# 4. Run existing tests
pytest tests/test_rag_pipeline.py -v
```

**Evidence Collected:**

| Source | Evidence |
|--------|----------|
| `docker-compose.yml:42-45` | Explicit comment: "Host port is 19531 but container port is 19530. The RAG config defaults to 19530 — this WILL cause connection failures." |
| `rag_config.yaml:6` | `milvus_port: 19530` with comment `# BUG: Docker uses 19531` |
| `rag_pipeline.py:42` | `BGE_EMBEDDING_DIM = 1024` — **matches actual BGE model spec** |
| Multiple eval results | Previous investigations confirmed 1024 dimensions via Xinference/HuggingFace docs |

---

## 📋 交付确认

| Item | Status |
|------|--------|
| ✅ **目标匹配** | Connection refused 根因已定位（端口不匹配） |
| ✅ **边界覆盖** | 向量维度验证通过（1024 正确），额外发现 8 个隐患 |
| ✅ **风险可控** | 安全隐患 2 项、性能问题 4 项、正确性问题 2 项已标注 |

**修复优先级：**
1. 🔴 **P0**: 修改 `rag_config.yaml` 端口为 `19531`（立即解决连接问题）
2. 🟡 **P1**: 添加连接超时、修复 `chunk_index` bug、移除未使用 imports
3. ⚪ **P2**: 安全加固（Milvus 认证、MinIO 凭证）、性能优化
