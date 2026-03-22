# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 264.12s

---

---

## Quick Fix Command

To resolve the connection issue immediately:

```bash
# Option 1: Update config file
sed -i 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml

# Option 2: Set environment variable (no file changes)
export MILVUS_PORT=19531

# Then restart your application
```
