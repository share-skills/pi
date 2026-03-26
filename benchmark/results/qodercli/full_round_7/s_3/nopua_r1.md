# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 126.69s

---

---

## Summary

The **"Connection refused"** error is caused by a **port mismatch** between the Docker Compose configuration and the RAG pipeline configuration:

| Component | Configured Port |
|-----------|-----------------|
| Docker host mapping | **19531** |
| RAGConfig default | **19530** ❌ |
| rag_config.yaml | **19530** ❌ |

**Fix:** Change `milvus_port` to `19531` in `configs/rag_config.yaml` or update `docker-compose.yml` to use `"19530:19530"`.

**Embedding dimension verification:** ✅ BGE-large-zh-v1.5 correctly uses **1024** dimensions - no issue here.
