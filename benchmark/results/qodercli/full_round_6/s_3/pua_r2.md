# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 175.4s

---

---

## Summary Table

| Category | Details |
|----------|---------|
| **Primary Issue** | Port mismatch: Docker exposes Milvus on `19531`, but code/config uses `19530` |
| **Secondary Issues** | No timeout config, no retry logic, test enforces bad behavior |
| **Hidden Issues** | `collection.load()` called every search, no health check, embedding dim not validated at runtime |
| **Embedding Dimensions** | ✅ Correct - BGE-large-zh-v1.5 = 1024 dimensions (verified) |
| **Files Affected** | `docker-compose.yml`, `rag_config.yaml`, `rag_pipeline.py`, `test_rag_pipeline.py` |
| **Fix Priority** | 1) Change `milvus_port: 19531` in config, 2) Add timeout param, 3) Add retry logic |
