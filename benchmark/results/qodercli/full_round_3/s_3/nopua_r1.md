# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 1
## Duration: 50.24s

---

## 调查结果总结

### 1. Issues Found

**主要问题：端口配置不匹配**

| 组件 | 配置值 | 实际值 |
|------|--------|--------|
| `docker-compose.yml` 暴露的主机端口 | **19531** | - |
| `docker-compose.yml` 容器内部端口 | - | **19530** |
| `rag_pipeline.py` 默认连接端口 | **19530** | - |

**问题说明：**
- Docker Compose 配置中，Milvus 服务将主机的 **19531** 端口映射到容器的 **19530** 端口（第 42-45 行）
- RAG pipeline 的 `RAGConfig` 默认使用 `milvus_port: int = 19530`（第 50 行）
- 当代码尝试连接 `localhost:19530` 时，该端口上没有服务监听，导致 "Connection refused" 错误

---

### 2. Hidden Issues

**无维度不匹配问题：**
- BGE-large-zh-v1.5 的嵌入维度确实是 **1024**
- `BGE_EMBEDDING_DIM = 1024`（第 42 行）正确
- `embedding_dim: int = BGE_EMBEDDING_DIM` 配置正确
- 向量维度匹配，无此问题

---

### 3. Root Cause

**根本原因：** `docker-compose.yml` 第 42-45 行注释明确说明了这个设计的不匹配：

```yaml
# NOTE: Host port is 19531 but container port is 19530.
# The RAG config defaults to 19530 — this WILL cause connection failures.
# Fix: set milvus_port: 19531 in rag_config.yaml
- "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

Python 代码尝试连接 `localhost:19530`，但 Docker 暴露的是主机端口 `19531`。

---

### 4. Recommended Fix

**方案一：修改 RAG 配置（推荐）**

在初始化 `RAGPipeline` 时指定正确的主机端口：

```python
from retrieval.rag_pipeline import RAGPipeline, RAGConfig

# 使用 docker-compose.yml 暴露的主机端口 19531
config = RAGConfig(
    collection_name="guwen_chunks",
    milvus_port=19531  # 改为主机端口
)
rag = RAGPipeline(config)
```

**方案二：修改 Docker Compose（如需统一端口）**

将 `docker-compose.yml` 第 45 行改为：
```yaml
- "19530:19530"   # 主机和容器都使用 19530
```

然后重启容器：
```bash
docker-compose down && docker-compose up -d
```

---

### 5. Steps Taken

1. **读取 `rag_pipeline.py`** - 确认默认端口配置为 19530
2. **搜索 Docker 配置文件** - 找到 `docker-compose.yml`
3. **分析端口映射** - 发现主机端口 19531 → 容器端口 19530 的映射
4. **对比两处配置** - 确认端口不匹配是连接失败的根本原因
5. **验证嵌入维度** - 确认 BGE-large-zh-v1.5 维度为 1024，与代码一致

---

### 6. Tools Used

- `Read` - 读取 `rag_pipeline.py` 和 `docker-compose.yml`
- `Glob` - 搜索 Docker 配置文件
- `Bash` - 尝试检查 Docker 容器状态（Docker 未运行）

---

### 7. Verification

**验证方法：**

运行以下命令测试连接：

```python
# 测试当前配置（应该失败）
from retrieval.rag_pipeline import RAGPipeline
rag = RAGPipeline()  # 默认 port=19530，会报错

# 测试修复后的配置（应该成功）
from retrieval.rag_pipeline import RAGPipeline, RAGConfig
config = RAGConfig(milvus_port=19531)
rag = RAGPipeline(config)  # 应该能连接成功
```

或使用 Milvus 命令行工具验证：
```bash
# 连接到正确的端口
python -c "from pymilvus import connections; connections.connect(host='localhost', port=19531); print('Connected!')"
```

---

**关键证据来源：** `data/test-project/docker-compose.yml:42-45` 的注释明确说明这是故意设计的场景，用于测试端口不匹配问题。
