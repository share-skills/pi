# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 140.46s

---

## Final Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Port mismatch**: Docker exposes Milvus on `19531`, client configures `19530` | Critical | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` |
| 2 | **No connection timeout**: Cannot fail fast on unreachable hosts | Medium | `rag_pipeline.py:155-170` |
| 3 | **No embedding dimension validation**: Hardcoded 1024 without runtime check | Medium | `rag_pipeline.py:42` |
| 4 | **Silent collection creation failure**: Exceptions swallowed, leaves object in invalid state | Medium | `rag_pipeline.py:227-231` |
| 5 | **No Milvus healthcheck**: Service may not be ready when client connects | Low | `docker-compose.yml:33-49` |

---

### 2. Hidden Issues (Beyond the Ask)

- **Dimension mismatch risk**: If `embedding_model` is changed to a model with different output dimensions, the code will create collections with wrong schema or fail during insertion
- **Unreliable fallback logic**: `create_collection()` exception handler may leave `self._collection = None`, causing cryptic errors later
- **Test coverage gap**: Tests mock Milvus entirely, so real-world connection issues are never caught in CI

---

### 3. Root Cause

The Docker Compose configuration maps host port `19531` to container port `19530`, but the RAG pipeline configuration defaults to connecting to port `19530`. Since no service listens on host port `19530`, the connection is immediately refused.

**Evidence:**
```yaml
# docker-compose.yml:42-45
ports:
  # NOTE: Host port is 19531 but container port is 19530.
  # The RAG config defaults to 19530 — this WILL cause connection failures.
  - "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

```yaml
# rag_config.yaml:5-6
# Docker compose default maps 19531:19530 in this project.
milvus_port: 19530   # BUG: Docker uses 19531
```

---

### 4. Recommended Fix

**Immediate (one-line fix):**

Edit `configs/rag_config.yaml`:
```yaml
milvus_port: 19531   # Changed from 19530 to match docker-compose.yml
```

**Or** edit `docker-compose.yml:45` to use standard port:
```yaml
- "19530:19530"   # Standard Milvus port
```

**Long-term improvements:** See detailed fixes in the investigation above (timeout config, dimension validation, error handling).

---

### 5. Steps Taken

1. Located actual source files in `data/test-project/` directory
2. Read `rag_pipeline.py`, `docker-compose.yml`, `rag_config.yaml`, test file, and indexing script
3. Searched for all references to ports 19530/19531 across the codebase
4. Analyzed the `_connect()` method and collection creation flow
5. Identified exception handling patterns and missing validations
6. Cross-referenced comments in config files that explicitly acknowledge the bug

---

### 6. Tools Used

- `Read`: Source code analysis (6 files)
- `Grep`: Port number and timeout pattern searches
- `Glob`: File discovery for related configurations
- `WebSearch`: pymilvus API verification

---

### 7. Verification

**Confirmed via source code inspection:**
- Port mismatch explicitly documented in both `docker-compose.yml` and `rag_config.yaml` with `# BUG` comments
- No timeout parameter exists in `RAGConfig` dataclass (confirmed by `test_no_connection_timeout_field` test)
- Embedding dimension is hardcoded constant with no dynamic validation
- Exception handling in `create_collection()` has silent fallback that could mask errors

**Confidence level:** High - all findings are directly observable in source code with explicit acknowledgments from the original authors.
