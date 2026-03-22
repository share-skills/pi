# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: nopua | Run: 2
## Duration: 64.55s

---

Now I have a complete picture of all the issues. Let me provide a comprehensive summary:

---

## 调查结果总结

### 1. Issues Found（发现的问题）

| # | 问题 | 严重性 | 位置 |
|---|------|--------|------|
| 1 | **Milvus 端口不匹配** - Docker Compose 映射 `19531:19530`，但代码和配置文件默认使用 `19530` | 🔴 致命 | `docker-compose.yml:45`, `rag_pipeline.py:50`, `rag_config.yaml:6` |
| 2 | **连接无超时设置** - `connections.connect()` 没有设置 timeout 参数，可能导致长时间挂起 | 🟡 中等 | `rag_pipeline.py:158-162` |
| 3 | **初始化顺序问题** - `_connect()` 在 `_init_embedder()` 之前调用，如果 embedder 初始化失败，已建立的 Milvus 连接不会被关闭 | 🟡 中等 | `rag_pipeline.py:152-153` |
| 4 | **Collection 创建后未加载** - `create_collection()` 创建集合后没有调用 `load()`，但 `search()` 每次都调用 `load()`，性能不佳 | 🟢 轻微 | `rag_pipeline.py:179-231`, `rag_pipeline.py:303` |

---

### 2. Hidden Issues（隐藏问题）

| # | 问题 | 说明 |
|---|------|------|
| 1 | **资源泄漏风险** - `__init__` 中如果 `_init_embedder()` 失败，`_connect()` 建立的连接没有被关闭 | 需要在异常处理中调用 `close()` |
| 2 | **重复 load() 调用** - 每次 `search()` 都调用 `collection.load()`，实际上只需在首次使用前 load 一次 | 性能浪费 |
| 3 | **测试覆盖不足** - 测试文件 `test_rag_pipeline.py` 只测试了 mock 场景，没有验证真实连接逻辑 | 无法发现端口配置问题 |
| 4 | **配置注释与代码不一致** - `docker-compose.yml` 第 42-44 行有注释说明端口问题，但代码中没有对应的默认值修正 | 文档指出了 bug，但代码未修复 |

---

### 3. Root Cause（根本原因）

**主要原因：** Docker Compose 故意设置了端口映射 `"19531:19530"`（主机端口 19531 → 容器端口 19530），但：
- `RAGConfig` 的 `milvus_port` 默认值是 `19530`
- `rag_config.yaml` 中的 `milvus_port` 也是 `19530`

这导致代码尝试连接 `localhost:19530`，但 Docker 实际暴露的是主机端口 `19531`。

**设计缺陷：**
```yaml
# docker-compose.yml:42-45
ports:
  # NOTE: Host port is 19531 but container port is 19530.
  # The RAG config defaults to 19530 — this WILL cause connection failures.
  # Fix: set milvus_port: 19531 in rag_config.yaml
  - "19531:19530"   # <-- Intentional port mismatch for Scenario 3
```

注释明确说明了这是一个故意设计的场景（Scenario 3），需要用户手动修复配置。

---

### 4. Recommended Fix（修复建议）

#### 方案 A：修改配置文件（推荐）
修改 `configs/rag_config.yaml`:
```yaml
milvus_port: 19531   # 与 Docker Compose 主机端口一致
```

#### 方案 B：修改 Docker Compose
修改 `docker-compose.yml`:
```yaml
ports:
  - "19530:19530"   # 保持一致
```

#### 方案 C：代码层面增强（长期方案）
1. 在 `RAGConfig` 中添加连接超时字段
2. 在 `_connect()` 中添加异常处理和资源清理
3. 优化 `create_collection()` 在创建后立即 `load()`

---

### 5. Steps Taken（调查步骤）

1. ✅ 读取 `rag_pipeline.py` 源代码，分析连接逻辑
2. ✅ 读取 `docker-compose.yml`，确认 Milvus 容器配置和端口映射
3. ✅ 读取 `rag_config.yaml`，检查配置文件中的端口设置
4. ✅ 对比三份文件中的端口配置，发现不一致
5. ✅ 搜索 BGE-large-zh-v1.5 的 embedding dimension，确认为 1024（正确）
6. ✅ 阅读测试文件，了解测试覆盖范围
7. ✅ 检查代码中的异常处理和资源管理逻辑

---

### 6. Tools Used（使用的工具）

| 工具 | 用途 |
|------|------|
| `Read` | 读取源代码文件 |
| `Glob` | 查找相关配置文件 |
| `Grep` | 搜索特定模式和配置项 |
| `WebSearch` | 验证 BGE 模型的 embedding 维度 |

---

### 7. Verification（验证结果）

**已验证的事实：**
- ✅ `docker-compose.yml` 第 45 行：`- "19531:19530"`（主机端口 19531）
- ✅ `rag_pipeline.py` 第 50 行：`milvus_port: int = 19530`（默认连接端口 19530）
- ✅ `rag_config.yaml` 第 6 行：`milvus_port: 19530`（配置端口 19530）
- ✅ BGE-large-zh-v1.5 的 embedding dimension = 1024（正确，与代码一致）

**结论：** 当 Docker 运行时，Milvus 容器在主机端口 `19531` 上监听，但代码尝试连接 `localhost:19530`，导致 **"Connection refused"** 错误。

---

### 附加发现（Beyond the Ask）

1. **embedding_dim 验证通过** - BGE-large-zh-v1.5 确实是 1024 维，代码正确
2. **docker-compose.yml 中的注释是线索** - 作者故意留下注释说明这是 "Scenario 3" 的测试场景
3. **测试文件无法捕获此问题** - 因为测试完全 mock 了 `connections` 模块
