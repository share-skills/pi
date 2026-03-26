# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 115.74s

---

## Summary

**Root Cause:** The "Connection refused" error is caused by a **port mismatch**. Docker Compose maps Milvus to host port `19531`, but the RAG pipeline configuration defaults to port `19530`.

**Immediate Fix:** Change `milvus_port` from `19530` to `19531` in `configs/rag_config.yaml`.

**Vector Dimensions:** Verified correct — BGE-large-zh-v1.5 uses 1024 dimensions, which matches both the code constant and config.

**Additional Issues Found:** 8 hidden issues including performance problems (uncached `load()` calls), missing retry logic, security concerns (no Milvus auth, hardcoded MinIO credentials), and a bug in `chunk_index` calculation.
