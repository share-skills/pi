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

## Eval 驱动优化规则

- **Eval 标准定义**：`benchmark/eval_criteria.md`，定义 8 个指标的 Pass 标准 + 9 场景通过率要求
- **发布门禁**：编译产物必须通过 P2.5-Eval 门禁（≥8/9 场景通过）方可进入 P3 分发
- **SKILL.md 修改同步链**：SKILL_META.md → COMPILER.md 编译 → SKILL.md（标准版+渐进Core版）。快速跑分优化可直接改 SKILL.md，但最终必须同步回 SKILL_META.md
- **迭代日志**：每轮 eval 结果记录到 `benchmark/iteration_logs/{round}_{timestamp}.md`
- **弱场景追踪**：VALIDATOR.md Section I 记录弱场景修复状态，eval_criteria.md 记录弱场景验证标准