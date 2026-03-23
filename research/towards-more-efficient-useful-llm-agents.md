# 迈向更高效、更有用的LLM代理

> 来源：李康旭（Kangwook Lee），KRAFTON 首席AI官 / Ludo Robotics 首席技术官
> 加州大学伯克利分校 BLISS 研讨会 · 2026 年 3 月 19 日

---

## 概述

每个人都在构建LLM代理。产品已经成型并投入使用——例如Claude Code、Codex、AutoResearch和OpenClaw。但我们究竟该如何构建它们呢？这本专著深入探讨其中的关键理念，其中许多理念源于解决生产系统中的实际问题：Terminus-KIRA（终端编码代理）、PUBG Ally（实时合作游戏代理）和 Smart Zoi（inZOI中的生命模拟代理）。

涵盖主题：上下文工程、技能、压缩、多智能体、递归语言模型、拉尔夫循环、测试时扩展以及内存驱动的自进化。

---

## 1. 什么是LLM代理？

LLM智能体是一种基于LLM的系统，它通过迭代地进行以下三个步骤来实现目标：

1. **观察（Observe）**：读取环境
2. **思考（Think）**：推理与决策
3. **行动（Act）**：调用工具/执行操作

循环往复，直到完成目标。这是核心循环，本专著中的其他所有内容都是对这一基本循环的变体或改进。

---

## 2. 工具调用（无循环）

最简单的构建模块是单个LLM调用，产生想法并执行行动。没有循环——只需一次调用。

```
context = task_instruction
generated_tokens = LLM(context)
thoughts, action = parse(generated_tokens)
exec(action)
```

一次调用，一次操作，一个结果。适用于简单任务："搜索 X"、"计算 Y"。

---

## 3. 代理循环（基本形式）

添加一个 while 循环：智能体持续运行直到任务完成。

```
token_history = task_instruction
while 任务尚未完成:
    generated_tokens = LLM(token_history)
    thoughts, action = parse(generated_tokens)
    output = exec(action)
    token_history += [thoughts, action, output]
```

**关键变化**：
- **while 循环**：代理持续运行
- **output**：反馈给下一次迭代
- **token_history**：记录所有过往交互

> 注：我们特意称之为"输出"而非"状态"。现实世界的系统并非马尔可夫系统，输出远比下一个"状态"复杂——它包含执行过程中观察到的所有内容：日志、信号、副作用，甚至奖励。

---

## 4. 上下文工程（Context Engineering）

### 核心问题

- token_history 随每次迭代增长
- 最终填满上下文窗口
- 每个令牌的生成计算量随上下文大小线性增长
- KV缓存容量也线性增长
- 大部分历史可能无关紧要

### 解决方案

将历史记录与 LLM 上下文分离，为每次迭代准备合适的上下文：

```
token_history = task_instruction
while 任务未完成:
    context = context_build(token_history, external_info)
    generated_tokens = LLM(context)
    thoughts, action = parse(generated_tokens)
    output = exec(action)
    token_history += [thoughts, action, output]
```

### 4.1 工具切换（Tool Swapping）

工具定义在系统提示符中。上下文工程允许在任何迭代中切换系统提示符，从而动态更改可用工具集。

```
context_build(token_history, external_info):
    tools = select_tools(current_task_phase)
    return system_prompt(tools) + token_history
```

例如，编码代理首先使用文件浏览工具，然后切换到编辑工具，最后切换到测试工具。

### 4.2 技能（Skills）

技能是按需加载的结构化（提示、工具集、指令）包。通过上下文工程自适应注入特定任务的提示。

```
context_build(token_history, external_info):
    relevant_skills = find_relevant_skill(token_history, external_info)
    return token_history + relevant_skills
```

**为什么不把所有内容放在一个巨大的提示中？** 上下文窗口有限。技能实现选择性加载——只在需要时加载需要的内容。

> ⚠️ **警告：技能也是让代理过拟合基准测试的最简单方式。** 特定任务的技能可以在不提高通用能力的情况下夸大评分。

**技能就是文本文件**，在相关时加载到上下文中。Claude Code 的真实示例：

```
# /commit -- a skill for creating git commits
When the user asks to commit changes:
1. Run git status and git diff to see all changes
2. Analyze the diff -- summarize the nature of the changes
3. Draft a concise commit message (1-2 sentences)
4. Stage relevant files (avoid secrets, .env, etc.)
5. Create the commit
```

**关键洞察**：技能 = 提示 + 工具 + 指令。仅在代理需要时加载。代理调试时不会看到 /commit 技能。

**持续学习**：由于技能只是文本，代理可以从经验中编写新技能、更新现有技能，甚至与其他代理共享——一种现代形式的去中心化学习。更新技能 = 更新提示。

### 4.3 压缩（Compaction）

当上下文窗口满时，压缩 token 历史：

```
context_build(token_history, external_info):
    return compaction(token_history)
```

**压缩策略取决于应用**：
- **编码代理**：output = [compiler_log, result]。日志长，结果短（"compile successful"）。移除日志，保留结果。
- **ML研究代理**：output = [training_curves, validation_loss]。曲线长，损失短。保留损失。
- **LLM 摘要**：LLM_summarizer(token_history) — 用另一个 LLM 压缩。

### 4.4 KV Cache 约束

上下文工程在迭代间改变上下文。但如果**前缀改变**，KV cache 失效，需要完全重新计算。

**方案：Masking（Manus, 2025）**

从一开始就将所有信息放入系统提示中。通过 logit masking 而非添加/删除来"屏蔽"无关部分。前缀永不改变，KV cache 始终复用。

> 通过从一开始就固定整个系统提示，前缀的 KV cache 只计算一次，在每次迭代中复用。代价是更长的初始提示，但节省随迭代次数复合增长。
> 来源：Manus Blog, "Context Engineering for AI Agents" (2025)

### 4.5 临时上下文（Ephemeral Context）

在稳定前缀**之后**附加迭代特定的上下文。此"临时"上下文出现一次且不存储。

```
while task not completed:
    context = token_history + log    // log 附加在前缀之后（临时！）
    generated_tokens = LLM(context)
    thoughts, action = parse(generated_tokens)
    output = exec(action)
    token_history += [thoughts, action, result]  // 只保留结果！
```

此技术用于 **PUBG Ally**，其中丰富的态势信息（敌人、血量、安全区）在**当前**至关重要，但在未来迭代中无用。

---

## 5. 多智能体和子智能体

### 核心洞察

**多智能体 = 程序化的上下文隔离**，类似面向对象编程。

### 问题

如果一个代理同时编码和审查，审查者会被编码者的思路偏差（确认偏差）。解决方案：给每个角色一个干净的上下文。

```
// 每个代理有自己的上下文
code = LLM_Agent("code it")
review = LLM_Agent("review it", code)

// 或迭代式：
while True:
    code = LLM_Agent("code it", review)
    review = LLM_Agent("review it", code)
```

### 子代理 = 干净的工具

不要膨胀主代理的上下文，而是生成子代理。其上下文在使用后丢弃；主代理只看到摘要。

```
// 主代理生成子代理
action: LLM_Agent("read input.txt and summarize it")
output: "input.txt is about local restaurants in Berkeley ..."
```

子代理的上下文可能因完整文件而膨胀，但主代理只看到简洁摘要。**这就是上下文隔离的实际效果**。

---

## 6. 递归语言模型（Recursive LMs）

> Zhang, Kraska, Khattab, "Recursive Language Models" (2025)

实际问题：假设 LLM 计划处理 file000.txt 到 file099.txt。实践中，它可能跟丢并漏掉 file078.txt。解决方案：让 LLM **编写程序**来编排子代理，保证所有文件都被处理。

```
summary = run_program("""
    for file in files:
        result += LLM_Agent("summarize " + file)
    return result
""")
```

这将上下文工程（通过子代理）与程序化控制结合。对较小的模型特别有效，它们从结构化编排中受益。

---

## 7. 虚假完成问题（False Completion）

### 核心问题

代理循环中 `while task not completed`——代理如何知道它完成了？

三种方式：
1. **可验证任务**（有检查器）— 简单
2. **固定时间/预算限制** — 也简单
3. **LLM 自己决定**（生成"done"动作）— 常见且**问题最大**

### 真实示例

在 Terminal-Bench-2（SWE/MLE 级别任务）上：基准代理（Terminus）+ Claude Opus 4.6 在时间限制内提交了 5 次结果。

**5 次中 5 次，代理自信地提交了错误答案。**
**~80% 的失败源于虚假完成。**

### 7.1 Ralph Loop（拉尔夫循环）

思路：添加一个**外循环**，由一个全新代理检查工作是否真正完成。

```
while True:                              // 外循环
    answer_not_changed = True
    token_history = []
    while True:                          // 内循环 -- 干净上下文，相同世界状态
        context = context_build(token_history, external_info)
        generated_tokens = LLM(context)
        thoughts, action = parse(generated_tokens)
        if action == done: break
        output, answer_not_changed = exec(action)
        token_history += [thoughts, action, output]
    if answer_not_changed: break         // 只有下一个代理没有发现需要更改时才退出
```

**关键**：每个内循环以**干净上下文**开始但使用相同世界状态。减少确认偏差——全新代理不受先前推理影响。

> github.com/snarktank/ralph

### 7.2 Terminus-KIRA 方案

一种既有效又高效的变体：

```
token_history = task_instruction
token_history_wo_thoughts = []

while True:
    context = context_build(token_history, external_info)
    generated_tokens = LLM(context)
    thoughts, action = parse(generated_tokens)

    if action == done:
        generated_tokens = LLM(token_history_wo_thoughts)  // 只用工作记录，不含思考
        thoughts, action = parse(generated_tokens)
        if action == done: break                            // 真正完成：无偏见代理也同意

    output = exec(action)
    token_history += [thoughts, action, output]
    token_history_wo_thoughts += [action, output]           // 只跟踪工作
```

**验证者只看"做了什么"（actions + outputs），不看"怎么推理的"（thoughts）。** 这消除了确认偏差，无需完整的外循环重启。

---

## 8. AutoResearch：当虚假完成不是问题时

AutoResearch（Andrej Karpathy）在 Twitter 上走红。将基本代理循环应用于自主 ML 研究——不需要 Ralph 循环。

**为什么不需要 Ralph？** 这是一个**进度可度量的任务**。目标：训练模型以获得更低的验证损失。损失要么下降了，要么没有——很难虚假声称完成。

提示本质上是：**LOOP FOREVER**。查看 git 状态。用实验想法调整 train.py。提交。运行实验。读取结果。如果 val_bpb 改善，保留提交。如果没有，git reset。记录结果。永不停止。

> **NEVER STOP**: 一旦实验循环开始，不要暂停询问人类是否应继续。人类可能正在睡觉。以每个实验约5分钟计，每小时约12个，一夜总共约100个。用户醒来时看到实验结果，全部自主完成。

进度（val_bpb）直接可度量——虚假完成在这里几乎不可能。

同样模式适用于：AlphaEvolve (DeepMind)、AdaEvolve (Cemri et al.)。

---

## 9. 超人级自动 RL 代理

类似 AutoResearch，但用于 **RL 工程**。不仅仅是超参数调优——代理还必须设计奖励以避免奖励黑客攻击。

通过 b-boying 蜘蛛演示：代理自主设计奖励函数并训练 RL 策略，迭代直到达到超人表现。

---

## 10. 代理的测试时扩展（Test-Time Scaling）

另一种正交方法：生成多个候选并选择最佳。但对代理的探索很少：

### 挑战

- **太贵**：运行整个代理循环多次比采样多个思维链追踪成本高得多
- **难以聚合**：代理输出不来自固定选项集，多数投票不直接适用
- **多数投票可能无效**：虚假完成率通常 >50%，所有错误的轨迹往往看起来相似——多数是错的

### 朴素方法

```
for i in range(N):                    // N = 测试时扩展因子
    history[i] = LLM_agent(task_instruction)
best = LLM("find the most promising work" + task_instruction + history)
```

结果：准确率提高了，但**主要对 P(success) > 50% 的任务有效**。LLM 隐式地在聚类候选并选择多数。当 P(success) < 50% 时，多数是错的——所以**反而有害**。

### 两两比较（BTL）

减少多数偏差，使用**两两比较**——LLM 永远不会同时看到所有候选。

```
for i in range(N):
    history[i] = LLM_agent(task_instruction)
for (i, j) in [N] x [N]:
    y[i,j] = LLM("which is more promising?" + history[i] + history[j])
s = BTL_solver(y)                     // Bradley-Terry-Luce 模型
return argmax(s)
```

**优势**：
- **无多数偏差**：两两比较不同时暴露所有候选。比较之间无上下文共享
- **更多计算 = 更小方差**：每对比较多次。比较本身也有测试时计算！

### 初步结果

| Agent | 基线（单次运行）| BTL 最佳（两两）| 提升 |
|-------|---------------|----------------|------|
| Terminus-KIRA | 76.2 | 81.3 | +5.1 |
| Terminus-2 | 62.9 | 67.0 | +4.1 |
| OpenSage GPT-5.3 | 78.4 | 81.1 | +2.7 |

---

## 11. OpenClaw：基于记忆的自进化代理

OpenClaw = 基本代理循环 + Ralph 循环 + **记忆更新**。每个任务后，代理更新自己的提示——实现跨任务持续学习。

```
token_history = system_prompt + memory + task_instruction
while True:
    context = context_build(token_history, external_info)
    generated_tokens = LLM(context)
    thoughts, action = parse(generated_tokens)
    if action == done:
        memory = memory_update(thought_history)    // 自进化！
        break
    output = exec(action)
    token_history += [thoughts, action, output]
```

**创造性记忆**：memory_update 可以是创造性的：总结会话、定义代理随时间更新的 IDENTITY、跨任务发展个性和特征。

---

## 12. 记忆实践：inZOI 和 PUBG Ally

- **inZOI**：尝试过自演化提示，但性格容易走向极端。最终采用用户自定义性格。销量超过100万份——首款搭载设备端LLM智能体的游戏。
- **PUBG Ally**：专注于友谊和过往游戏的回忆。"还记得我们赢下那场比赛吗？"随时间推移，让盟友感觉像真正的队友。

---

## 13. 开放性挑战

- **主动性**——代理何时应主动与你沟通？何时应代表你采取行动？
- **快速反应**——系统 1/系统 2 架构（参见 Helix）
- **蒸馏**——从LLM代理到SLM代理。并非易事（离策略、模型共享）
- **多模态**——（STT → LLM → TTS）会丢失信息。多模态模型应作为核心模型
- **评估**——代理的输出复杂、不确定，难以评分
- **规划**——LLM 不擅长探索/开发。外部搜索有所帮助（参见 TAPE、ReJump）

---

## 总结

| 主题 | 要点 |
|------|------|
| **代理循环** | 简单：观察、思考、行动，通过工具调用重复 |
| **上下文工程** | 关键设计空间：技能、压缩、临时上下文、KV缓存约束 |
| **多智能体/子智能体/递归LM** | 不同形式的上下文隔离和程序控制 |
| **虚假完成** | 生产环境首要问题。Ralph 循环、进度测量和 BTL 可解决 |
| **记忆** | 支持任务间连续性和自进化（OpenClaw、inZOI、PUBG Ally） |
| **开放挑战** | 主动性、快速反应、蒸馏、多模式、评估、规划 |

> 我们处于早期阶段。或许是通信领域的20世纪50年代。
> **去构建**（真正的工程始于实际问题），**去澄清**（其本质类似于控制理论、通信理论、统计推断）。

---

## PI 落实对照

### ✅ 已完整落实

| 论文洞察 | PI 实现 |
|---------|--------|
| Skills 按需加载 | pi-progressive 渐进加载架构（Core + references/ 按角色加载） |
| Skills 过拟合警告 | COMPILER.md "通用能力审计（防 Benchmark Overfitting）" |
| Terminus-KIRA 反偏差验证 | A1 反偏差验证："交付前只看做了什么（diff/输出），不回顾推理过程" |
| Multi-agent 上下文隔离 | A3 反偏差审查+子Agent隔离 |
| Compaction 信息分级 | A2 信息分级：临时信息→只保留结论；持久信息→写入历史 |
| Memory-based self-evolution | 自演化协议 + A6 经验沉淀 |
| False Completion 防护 | 改必验证 + 说而不做 + 证据门 + 交付六令 + **虚假完成双重检查协议**(§8.6) |
| Test-Time Scaling / BTL | 致人术第四式·方案比选 + **两两比较法**(§3.2)：≥3候选逐对比较防多数偏差 |
| Progress-Measurable 任务判别 | 查标·定锚 + **进度可度量性判别**(§8.3)：可度量/可验证/不可度量三档分类 |
| 虚假完成作为 #1 风险 | 反偏差验证升级为"**代理失败首因防线**" + 不可度量任务高危标注 |

### ⚙️ 部分落实（架构层已覆盖，可深化）

| 论文洞察 | 当前状态 |
|---------|---------|
| Ralph Loop 外循环验证 | A3 子Agent隔离已有基础；可在团队协作层增加独立 Agent 复检 |
