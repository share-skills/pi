# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 116.78s

---

---

## Summary

**Root Cause:** Docker Compose maps Milvus to host port `19531`, but the RAG config and code default to port `19530`. Connection attempts to `localhost:19530` fail with "Connection refused" because nothing listens there.

**Quick Fix:** Change `milvus_port: 19531` in `configs/rag_config.yaml`.

**Embedding Dimensions:** Verified correct - BGE-large-zh-v1.5 uses 1024 dimensions, matching the code.
