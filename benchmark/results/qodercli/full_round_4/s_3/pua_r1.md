# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 1
## Duration: 163.61s

---

## Summary

**Root Cause:** Port mismatch - Docker exposes Milvus on host port `19531`, but the RAG pipeline tries to connect on port `19530`.

**Quick Fix:** Change `milvus_port: 19530` to `milvus_port: 19531` in your config file or pass it when constructing `RAGConfig`.

**Embedding Dimensions:** Verified correct - BGE-large-zh-v1.5 uses 1024 dimensions, matching the code's `BGE_EMBEDDING_DIM = 1024`.
