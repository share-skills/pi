# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 113.89s

---

## 训练模块生产就绪性审计

### 执行摘要

**评估结果**: ⚠️ **不具备生产就绪性**

核心训练逻辑功能正常，但缺少关键的生产环境保障措施：检查点恢复、数据验证、错误处理和可复现性控制。在运行真实训练任务前，至少需要 2-3 天的集中工程修复。

---

### 1. 发现的问题

| # | 问题 | 严重程度 | 位置 |
|---|------|----------|------|
| 1 | **无检查点恢复机制** | 高 | `trainer.py` |
| 2 | **训练前无数据验证** | 高 | `trainer.py:train()` |
| 3 | **GRPO 训练器完全不可用** | 高 | `trainer.py:GRPOTrainer` |
| 4 | **预设中硬编码数据集路径** | 中 | `config_builder.py` |
| 5 | **无训练失败错误处理** | 高 | `trainer.py` |
| 6 | **eval_steps 可为 None 导致崩溃** | 中 | `trainer.py:_create_training_args()` |
| 7 | **过时的示例代码** | 中 | `example_usage.py` |
| 8 | **不支持分布式训练** | 中 | `trainer.py` |
| 9 | **缺少依赖要求文件** | 中 | 项目根目录 |
| 10 | **BLEU 分数实现 bug** | 低 | `evaluator.py` |

---

### 2. 隐藏问题（超出询问范围）

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| H1 | **内存泄漏风险**: 评估后未清理 CUDA 缓存 | 长时间运行 OOM | `evaluator.py` |
| H2 | **静默数据丢失**: 无效 JSONL 行仅记录不追踪 | 训练数据缺失 | `data_loader.py:252` |
| H3 | **标签 masking bug**: 仅基于 instruction 长度 masking，忽略 system prompt | 损失计算错误 | `data_loader.py:89-95` |
| H4 | **竞态条件**: 随机 shuffle 无固定种子 | 结果不可复现 | `data_loader.py:214` |
| H5 | **困惑度计算错误**: 仅在 output 上计算损失，非完整序列 | 困惑度分数虚高 | `evaluator.py:196-206` |
| H6 | **无早停机制**: 即使发散也跑满 epoch | 浪费算力 | `trainer.py` |
| H7 | **配置验证警告被忽略**: `validate()` 返回警告但无强制执行 | 无效配置进入训练 | `config_builder.py` |
| H8 | **模板不一致**: ChatML 模板使用繁体中文 system prompt，训练数据可能不一致 | 领域不匹配 | `data_loader.py:29-37` |

---

### 3. 根本原因分析

**主要根本原因:**

1. **抽象层不完整**: `TrainingConfig` 和 `ConfigBuilder` 解耦——预设返回的 dict 可能包含 `TrainingConfig` 中不存在的键，导致静默丢弃

2. **防御性编程缺失**: 无验证：
   - 分词前的数据集内容
   - 加载大模型前的 GPU 内存
   - 恢复时的检查点完整性
   - 外部库可用性

3. **未完成的技术债务**: `GRPOTrainer` 是存根，但暴露在公共 API 中

4. **可复现性缺口**: 随机操作缺乏种子控制

---

### 4. 推荐修复方案

#### 关键修复（生产前必须修复）

```python
# trainer.py - 添加检查点恢复
def train(self, resume_from_checkpoint: Optional[str] = None):
    """执行完整训练流程"""
    logger.info("Starting training pipeline")
    
    model, tokenizer = self._load_model()
    dataset = self._load_dataset()
    self._validate_dataset(dataset)  # 新增
    
    training_args = self._create_training_args()
    
    self._trainer = SFTTrainer(...)
    
    logger.info("Starting training...")
    
    # 处理恢复
    if resume_from_checkpoint:
        logger.info(f"Resuming from checkpoint: {resume_from_checkpoint}")
    
    try:
        self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    except Exception as e:
        logger.error(f"Training failed: {e}")
        self._save_emergency_checkpoint()  # 新增
        raise
    
    self._save_model()
    logger.info("Training complete!")
```

```python
# trainer.py - 添加数据集验证
def _validate_dataset(self, dataset):
    """训练前验证数据集"""
    required_fields = ["input_ids", "labels", "attention_mask"]
    
    train_ds = dataset["train"] if "train" in dataset else dataset
    if len(train_ds) == 0:
        raise ValueError("Training dataset is empty")
    
    sample = train_ds[0]
    for field in required_fields:
        if field not in sample:
            raise ValueError(f"Dataset missing required field: {field}")
    
    lengths = [len(s["input_ids"]) for s in train_ds[:100]]
    if max(lengths) > self.config.max_seq_length:
        logger.warning(f"Some samples exceed max_seq_length")
```

```python
# trainer.py - 修复 eval_steps 崩溃
def _create_training_args(self) -> TrainingArguments:
    has_eval_data = self.config.eval_dataset_path is not None
    
    return TrainingArguments(
        # ... 其他参数 ...
        eval_steps=self.config.eval_steps if has_eval_data else 500,
        evaluation_strategy="steps" if has_eval_data else "no",
    )
```

```python
# data_loader.py - 修复可复现性
def load(self, data_path: str, eval_ratio: float = 0.05, seed: int = 42) -> tuple:
    """加载数据并返回训练/评估数据集"""
    samples = self._read_jsonl(data_path)
    if not samples:
        raise ValueError(f"No samples loaded from {data_path}")

    import random
    random.seed(seed)  # 修复：添加种子
    random.shuffle(samples)
```

#### 高优先级

```yaml
# 添加 requirements.txt
transformers>=4.35.0
trl>=0.7.0
peft>=0.6.0
datasets>=2.14.0
torch>=2.0.0
bitsandbytes>=0.41.0
rouge_score>=0.1.2
pyyaml>=6.0
tqdm>=4.65.0
click>=8.0.0
tensorboard>=2.14.0
```

#### 中优先级

1. **移除或实现 GRPO 训练器** - 完全实现或移至 `experimental/`
2. **添加分布式训练支持** - 使用 `accelerate` 库
3. **修复 evaluator BLEU 平滑** - 为短序列添加平滑
4. **文档化预设限制** - 注明路径必须覆盖

---

### 5. 调查步骤

1. 阅读训练模块全部 5 个源文件
2. 分析数据流：Config → DataLoader → Trainer → Evaluator
3. 识别每个阶段的失败点
4. 交叉引用模块间的一致性
5. 审查过时代码标记

---

### 6. 使用的工具

- 文件读取（全部 5 个源文件）
- 代码模式搜索（TODO 注释、存根实现）
- 依赖分析（从导入推断）
- 控制流分析（追踪执行路径）

---

### 7. 验证证据

| 发现 | 证据 |
|------|------|
| 无恢复支持 | `trainer.py:train()` 无 `resume_from_checkpoint` 参数 |
| GRPO 不可用 | `trainer.py:287` 抛出 `NotImplementedError` |
| eval_steps bug | 第 253 行：条件为 None 时 HF Trainer 可能崩溃 |
| 标签 masking bug | `data_loader.py:89-95` 仅 mask instruction，忽略 system prompt |
| shuffle 无种子 | `data_loader.py:214` 调用 `random.shuffle()` 无前导 `seed()` |
| 过时示例 | `example_usage.py` 明确标注适用于 v0.2.0，当前为 v0.4.x |
