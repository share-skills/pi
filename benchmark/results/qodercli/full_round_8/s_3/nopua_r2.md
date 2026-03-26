# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 191.71s

---

---

## 最终报告

### 问题清单

| # | 问题 | 严重程度 | 位置 |
|---|------|----------|------|
| 1 | **Docker 端口映射与 RAG 配置不匹配** | 严重 | `docker-compose.yml:45` + `rag_pipeline.py:50` |
| 2 | **缺少连接超时参数** | 中等 | `rag_pipeline.py:155-170` |
| 3 | **重复低效的 collection.load() 调用** | 低 | `rag_pipeline.py:303` |

### 隐藏问题

1. **每次搜索都调用 `load()`** - Milvus 集合只需加载一次到内存，无需每次查询都加载
2. **无重试机制** - 网络波动或容器启动慢会导致立即失败
3. **初始化时加载嵌入模型** - 即使只做搜索也会阻塞初始化
4. **无健康检查** - 连接断开后操作会静默失败

### 根本原因

**连接拒绝的主因：** Docker 将主机端口 `19531` 映射到容器端口 `19530`，但 RAG 配置默认使用 `19530`。从主机网络访问时，Python 代码尝试连接 `localhost:19530`，但 Milvus 实际暴露在 `localhost:19531`。

**Embedder 正常工作的原因：** 嵌入模型本地运行，不依赖 Milvus 连接。维度配置正确（1024）。

### 推荐修复方案

1. **修复端口配置** - 将 `RAGConfig.milvus_port` 改为 `19531`，或修改 Docker 映射为 `19530:19530`
2. **添加超时参数** - `connections.connect(..., timeout=5.0)`
3. **优化 load() 调用** - 仅在创建集合时加载一次，移除 search 中的重复调用

### 调查步骤

1. 读取项目结构定位关键文件
2. 分析连接代码和 Docker 配置
3. 验证嵌入维度（BGE-large-zh-v1.5 = 1024）
4. 查询 pymilvus API 文档确认超时参数
5. 发现隐藏的性能问题

### 使用工具

- `Glob` / `Grep` / `Read` - 代码分析
- `WebSearch` / `WebFetch` - 验证外部信息
