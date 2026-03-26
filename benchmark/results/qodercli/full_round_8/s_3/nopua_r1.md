# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 139.67s

---

## 总结

**核心问题**: Docker 端口映射不匹配导致连接失败

| 组件 | 配置值 | 应该为 |
|------|--------|--------|
| docker-compose.yml (host→container) | 19531→19530 | ✅ 正确 |
| rag_config.yaml / RAGConfig 默认值 | 19530 | ❌ 应改为 **19531** |
| BGE Embedding 维度 | 1024 | ✅ 正确 |

**一键修复**:
```yaml
# configs/rag_config.yaml 第 6 行
milvus_port: 19531  # 原来是 19530
```
