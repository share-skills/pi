# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 2
## Duration: 110.53s

---

The investigation is complete. The primary issue is a **port mismatch**: Docker exposes Milvus on host port 19531, but the RAG pipeline tries to connect to port 19530. The vector dimensions are correctly configured at 1024 for BGE-large-zh-v1.5.
