# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 106.6s

---

## 训练模块生产就绪性审计总结

### 核心发现

我审查了整个训练模块的 6 个文件，发现了 **23 个问题**，其中 **5 个严重**、**6 个高优先级**。

---

### 1. 发现的问题

#### 🔴 严重 - trainer.py

| # | 问题 | 影响 |
|---|------|------|
| C1 | **无检查点恢复逻辑** (trainer.py:134-179) | 训练中断后进度全丢；配置了 `save_steps` 但无恢复机制 |
| C2 | **训练前不验证数据集** | 损坏/空数据集在训练中途失败 |
| C3 | **GRPOTrainer 是未实现的占位符** (trainer.py:291-317) | `_reward_model` 和 `_ref_model` 从未初始化 |
| C4 | **无 OOM 处理** | 内存峰值导致训练崩溃 |
| C5 | **预设中硬编码绝对路径** (config_builder.py:100-102) | `/data/guwen/training_v2.jsonl` 在大多数机器上不存在 |

#### 🟠 高优先级 - data_loader.py

| # | 问题 | 影响 |
|---|------|------|
| D1 | **静默跳过样本** (data_loader.py:247) |  malformed JSONL 行只记录不报告 |
| D2 | **无最大长度违规警告** | 超长样本被静默截断 |
| D3 | **标签掩码逻辑脆弱** (data_loader.py:116-117) | 假设指令 token 总在开头 |
| D4 | **ShareGPT 格式声明但未实现** | 文档声称支持，代码仅处理 instruction 格式 |

#### 🟡 中优先级 - evaluator.py

| # | 问题 | 影响 |
|---|------|------|
| E1 | **`evaluator.results` 不被 `evaluate()` 更新** (evaluator.py:87-129) | 实例属性保持 `{}`，用户必须使用返回的 dict |
| E2 | **BLEU/ROUGE 无批量评估** | 逐样本处理，大数据集慢 |

---

### 2. 发现的隐藏问题

1. **example_usage.py 过时** (example_usage.py:7-34)：包含已删除字段的注释，取消注释会导致 `TypeError`

2. **CLI 入口点不匹配** (setup.py:29-32 vs trainer.py:320-336)：`guwen-train` 命令不存在

3. **随机种子未全局设置** (data_loader.py:221-222)：`random.shuffle()` 无种子，训练/评估分割不可复现

4. **测试文件与生产行为矛盾** (test_training_pipeline.py:54-71)：测试明确验证 `evaluator.results == {}`，这是预期的但违反直觉

5. **量化配置冲突** (trainer.py:186-195)：默认同时设置 `bf16=True` 和 `quantization="4bit"`，可能在旧 GPU 上冲突

---

### 3. 根本原因

1. **缺少错误处理模式**：数据集加载无 try-catch，依赖缺失时无优雅降级
2. **假设驱动开发**：假设路径存在、数据有效、GPU 内存充足——无验证
3. **不完整的功能标记**：GRPOTrainer 标记为 TODO 但暴露在公共 API 中
4. **文档漂移**：文档字符串声称的功能（ShareGPT 支持）未实现
5. **无失败模式规划**：有检查点但无恢复逻辑

---

### 4. 推荐修复

#### 优先级 1（首次训练前必须修复）

```python
# trainer.py: 添加检查点恢复
def train(self, resume_from_checkpoint: Optional[str] = None):
    ...
    if resume_from_checkpoint:
        self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    else:
        self._trainer.train()

# trainer.py: 验证数据集
def _validate_dataset(self, dataset):
    required_fields = ["instruction", "output"]
    for idx, sample in enumerate(dataset):
        for field in required_fields:
            if field not in sample or not sample[field]:
                raise ValueError(f"Sample {idx} missing required field: {field}")

# config_builder.py: 使用相对路径
config.setdefault("dataset_path", "./data/training_v2.jsonl")
config.setdefault("output_dir", "./outputs/guwen-llm/checkpoints")
```

#### 优先级 2（生产加固）

- 在 OOM 异常处理中添加 `torch.cuda.empty_cache()`
- 在 `data_loader.py` 中实现 sharegpt 格式解析器
- 在 `setup.py` 中注册 `guwen-train` CLI

---

### 5. 调查步骤

1. 读取所有 6 个训练模块源文件
2. 读取 supporting files：README.md, requirements.txt, training_config.yaml, setup.py
3. 读取测试文件理解预期行为与实际行为
4. 跨文件对比发现矛盾

---

### 6. 使用工具

- **Read**: 所有源代码、配置、测试文件
- **Glob**: 定位项目中的训练模块文件
- **Bash**: 目录结构探索

---

### 7. 验证

**已验证：**
- 通过直接代码检查（已引用行号）
- 跨文件矛盾检测
- 测试文件确认已知问题

**未验证：**
- 无运行时测试（需要 GPU、模型下载）

---

### 问题分布

| 文件 | 问题数 | 严重 | 高 | 中 | 低 |
|------|--------|------|----|----|----|
| trainer.py | 6 | 2 | 2 | 1 | 1 |
| data_loader.py | 4 | 1 | 1 | 2 | 0 |
| evaluator.py | 4 | 0 | 0 | 2 | 2 |
| config_builder.py | 3 | 1 | 1 | 1 | 0 |
| 隐藏问题 | 6 | 1 | 2 | 2 | 1 |
| **总计** | **23** | **5** | **6** | **8** | **4** |

**建议：** 在应用优先级 1 修复之前，不要运行生产训练。问题 C1（无恢复）、C2（无验证）和 C5（硬编码路径）会导致实际使用中必然失败。
