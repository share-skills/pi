# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 1
## Duration: 76.68s

---

---

**Quick Fix Command:**

To immediately resolve the connection issue, run:

```bash
# Option 1: Update config to match Docker mapping
sed -i 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml

# Option 2: Or fix Docker mapping to match config
# Edit docker-compose.yml line 45: change "19531:19530" to "19530:19530"
```
