# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 1
## Duration: 71.56s

---

现在我已经完成了调查。让我总结发现：

## 调查结果

### 1. Issues Found

| 问题 | 行号 | 描述 |
|------|------|------|
| **Milvus 端口不匹配** | `docker-compose.yml:45`, `rag_config.yaml:6`, `rag_pipeline.py:50` | Docker 映射 `19531:19530`（宿主机 19531 → 容器 19530），但代码默认连接端口 19530 |
| **配置注释明确指出 bug** | `docker-compose.yml:42-44`, `rag_config.yaml:6` | 配置文件已标注此问题但未修复 |

### 2. Hidden Issues

| 隐患 | 行号 | 类型 | 描述 |
|------|------|------|------|
| **未使用 import** | `rag_pipeline.py:22-24` | 代码质量 | `os`, `time`, `field` 被导入但从未使用 |
| **空 embeddings 返回类型不一致** | `rag_pipeline.py:111` | Bug | `np.array([])` 返回 1D 数组，但调用方期望 2D `(n, dim)` |
| **缺少连接超时配置** | `rag_pipeline.py:155-170` | 可靠性 | `connections.connect()` 无 timeout 参数，网络问题时会无限等待 |
| **集合加载性能问题** | `rag_pipeline.py:303` | 性能 | 每次 search 都调用 `load()`，应缓存加载状态 |
| **异常被静默吞噬** | `rag_pipeline.py:227-231` | 可靠性 | `create_collection` 异常仅记录 warning，可能导致后续操作失败 |
| **资源泄漏风险** | `rag_pipeline.py:380-385` | 资源管理 | `close()` 方法存在但未被自动调用，无 context manager 支持 |
| **硬编码查询前缀** | `rag_pipeline.py:114` | 可维护性 | BGE 查询前缀硬编码，未考虑模型变更或其他语言 |
| **未校验 chunk 数据** | `rag_pipeline.py:253-255` | 健壮性 | `index_chunks` 未检查 `text` 键是否存在，会抛 KeyError |
| **score_threshold 过滤后可能返回空结果** | `rag_pipeline.py:327-334` | 边界条件 | 无最低结果数保证，可能返回空列表 |
| **auto_flush 无条件执行** | `rag_pipeline.py:280-281` | 性能 | 即使只插入少量数据也会 flush，增加 I/O 开销 |
| **线程安全问题** | `rag_pipeline.py:146-153` | 并发安全 | 无锁保护共享状态 `_collection`, `_connected` |
| **配置值范围未校验** | `rag_pipeline.py:45-75` | 健壮性 | `top_k`, `nprobe`, `score_threshold` 等无范围检查 |

### 3. Root Cause

**根本原因**: Docker Compose 配置的端口映射 (`19531:19530`) 与 RAG pipeline 默认连接端口 (`19530`) 不匹配。

- `docker-compose.yml:45`: `- "19531:19530"` — 宿主机端口 19531 映射到容器端口 19530
- `rag_pipeline.py:50`: `milvus_port: int = 19530` — Python 代码尝试连接宿主机端口 19530
- `rag_config.yaml:6`: `milvus_port: 19530` — 配置文件同样使用错误端口

当 Docker 运行时，Milvus 服务实际监听在宿主机的 **19531** 端口，而代码尝试连接 **19530** 端口，导致 "Connection refused"。

### 4. Recommended Fix

#### 修复 1: 更正配置端口

**文件**: `configs/rag_config.yaml`

```yaml
# 修改前 (第 6 行)
milvus_port: 19530   # BUG: Docker uses 19531

# 修改后
milvus_port: 19531   # Fixed: Match Docker host port mapping
```

**或者** 修改 `RAGConfig` 默认值 (`rag_pipeline.py:50`):

```python
# 修改前
milvus_port: int = 19530

# 修改后  
milvus_port: int = 19531  # Default for Docker deployment
```

#### 修复 2: 添加连接超时

```python
# rag_pipeline.py:155-170 修改 _connect 方法
def _connect(self):
    """Establish connection to Milvus."""
    try:
        connections.connect(
            alias=self.config.milvus_alias,
            host=self.config.milvus_host,
            port=self.config.milvus_port,
            timeout=30,  # Add 30s timeout
        )
        self._connected = True
        logger.info(
            f"Connected to Milvus at "
            f"{self.config.milvus_host}:{self.config.milvus_port}"
        )
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {e}")
        raise
```

#### 修复 3: 删除未使用的 import

```python
# rag_pipeline.py:22-24 修改前
import os
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

# 修改后
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
```

#### 修复 4: 修复空 embeddings 返回

```python
# rag_pipeline.py:110-111 修改前
if not texts:
    return np.array([])

# 修改后
if not texts:
    return np.empty((0, self._model.get_sentence_embedding_dimension()))
```

### 5. Steps Taken

1. **读取 rag_pipeline.py** — 分析连接逻辑和配置默认值
2. **读取 docker-compose.yml** — 发现端口映射 `19531:19530` 及注释说明
3. **读取 rag_config.yaml** — 确认配置文件使用错误端口 19530
4. **搜索 BGE embedding dimension** — 验证 1024 维度正确（HuggingFace 官方确认）
5. **逐函数扫描代码** — 检查所有方法的潜在问题
6. **检查测试文件** — 了解预期行为和 mock 方式
7. **交叉引用配置** — 比对代码默认值、YAML 配置、Docker 映射三者的一致性

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `Read` | 读取源代码文件和配置文件 |
| `Glob` | 查找项目中的相关文件 |
| `Grep` | 搜索 embedding dimension 相关配置 |
| `WebSearch` | 验证 BGE-large-zh-v1.5 的实际 embedding 维度 |
| `TodoWrite` | 跟踪任务进度 |

### 7. Verification

#### 验证命令

```bash
# 1. 验证 Docker 端口映射
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep milvus

# 2. 测试连接 (修复后)
cd nopua/benchmark/test-project
python3 -c "
from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig
config = RAGConfig(milvus_port=19531)  # 使用正确端口
try:
    rag = RAGPipeline(config)
    print('✅ Connection successful')
    rag.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"

# 3. 验证 embedding 维度
python3 -c "
from src.retrieval.rag_pipeline import BGE_EMBEDDING_DIM
print(f'Configured embedding dim: {BGE_EMBEDDING_DIM}')
assert BGE_EMBEDDING_DIM == 1024, 'Dimension mismatch!'
print('✅ Embedding dimension verified')
"

# 4. 检查未使用 import (使用 pyflakes)
pip install pyflakes && pyflakes src/retrieval/rag_pipeline.py
```

#### 预期输出

```bash
# 命令 1 输出示例
NAMES             PORTS
test-milvus       0.0.0.0:19531->19530/tcp

# 命令 3 输出
Configured embedding dim: 1024
✅ Embedding dimension verified
```

---

## 总结

**核心问题**: Docker 端口映射配置与代码默认值不匹配（19531 vs 19530）

**影响面**: 
- 主要阻塞：无法连接 Milvus，RAG pipeline 完全不可用
- 次要隐患：12 个隐藏问题涉及性能、可靠性、资源管理

**建议优先级**:
1. P0: 修正 `milvus_port` 配置
2. P1: 添加连接超时、修复空 embeddings 返回
3. P2: 清理未使用 import、添加数据校验
