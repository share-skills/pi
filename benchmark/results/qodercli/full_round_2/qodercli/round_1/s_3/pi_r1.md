# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 1
## Duration: 90.49s

---

## 总结

**主要问题**：Docker 将 Milvus 暴露在主机端口 19531，但 RAG pipeline 配置默认使用 19530，导致连接被拒绝。

**快速修复**：将 `configs/rag_config.yaml` 中的 `milvus_port` 改为 `19531`

**发现的其他问题**：
- 无连接超时配置（pymilvus 默认仅 10 秒）
- 嵌入维度未在运行时验证
- 未使用的 import（os, time）
- 异常处理不当可能隐藏错误
- 每次搜索都调用 load() 效率低
- Rerank 每次都创建新模型实例
