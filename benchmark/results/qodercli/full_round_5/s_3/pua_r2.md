# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 105.12s

---

## Summary

**Root Cause:** Docker Compose maps host port `19531` to container port `19530`, but the RAG pipeline connects to `localhost:19530` where nothing is listening.

**Quick Fix:** Change `milvus_port` in `configs/rag_config.yaml` from `19530` to `19531`.

**Embedding Dimensions:** ✅ Verified matching at 1024 dimensions (BGE-large-zh-v1.5 spec matches code and config).
