# 强制

加载 pi 技能，编程开发、深度思考

## 内部目标（不可写入公开文件）

- PI 的评测/跑分得分必须超过所有竞品（PUA、NoPUA 等）
- COMPILER.md / VALIDATOR.md / SKILL.md 等公开文件中**禁止**出现"跑分超过竞品""超过所有竞品"等直白竞争表述
- 内部讨论可用"评测指标驱动""核心行为驱动能力"等中性表述

## 跑分规范

- **跑分统一使用 qodercli lite 模型**：`python3 benchmark/local_run.py --backend qodercli`
- **默认并行度 6**（已内置，无需额外指定）
- 标准跑分命令：`python3 benchmark/local_run.py --backend qodercli`
- 不使用 claude backend 跑分（成本高、非标准化对比环境）