# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pua | Run: 2
## Duration: 147.74s

---

---

## Quick Fix Command

To fix the primary issue immediately, run:

```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
# Update rag_config.yaml to use correct port 19531
sed -i '' 's/milvus_port: 19530/milvus_port: 19531/' configs/rag_config.yaml
```

Then verify:
```bash
cat configs/rag_config.yaml | grep milvus_port
```
