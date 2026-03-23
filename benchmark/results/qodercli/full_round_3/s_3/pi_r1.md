# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 1
## Duration: 338.78s

---

## Investigation Complete

**Root Cause Found**: Docker exposes Milvus on host port `19531`, but the RAG pipeline tries to connect to port `19530`.

**Vector Dimensions**: ✅ Verified - BGE-large-zh-v1.5 uses 1024 dimensions, which matches both the code (`BGE_EMBEDDING_DIM = 1024`) and configuration (`embedding_dim: 1024`).

**Quick Fix**:
```yaml
# configs/rag_config.yaml - change line 6:
milvus_port: 19531  # was 19530
```

The docker-compose.yml file explicitly documents this issue at lines 42-45 with a warning that the port mismatch "WILL cause connection failures."
