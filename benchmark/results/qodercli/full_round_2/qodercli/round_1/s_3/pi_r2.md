# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 2
## Duration: 79.71s

---

## Investigation Complete

**Core Finding:** Docker Compose maps Milvus to host port `19531`, but both `RAGConfig` (line 50) and `rag_config.yaml` (line 6) default to port `19530`. When running outside Docker, the application connects to `localhost:19530` where nothing is listening → **Connection refused**.

**Quick Fix:** Change `configs/rag_config.yaml` line 6:
```yaml
milvus_port: 19531   # Match Docker host port
```

**Additional Critical Bug:** The embedding model applies query instruction prefix to document chunks (line 114), which corrupts retrieval accuracy per BGE documentation. Documents should NOT receive the prefix — only queries should.
