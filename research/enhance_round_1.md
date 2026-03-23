# PI SKILL 增强 Round 1 — 基于 LLM Agent 前沿论文的优化

> 日期：2026-03-22
> 来源论文：《迈向更高效、更有用的LLM代理》— 李康旭 (Kangwook Lee)
> 发表：UC Berkeley BLISS Seminar · 2026-03-19
> 原文：https://kangwooklee.com/talks/2026_03_BLISS/bliss_seminar_monograph.html
> 身份：KRAFTON 首席人工智能官 / Ludo Robotics 首席技术官
> 产品实践：Terminus-KIRA（编码Agent）、PUBG Ally（实时游戏Agent）、Smart Zoi（inZOI 生命模拟Agent）

---

## 论文核心洞见摘要

### 1. Agent 循环的本质

Agent = Observe-Think-Act 循环 + while(not done)。论文中其他所有内容都是对这一基本循环的变体或改进。

### 2. 上下文工程 (Context Engineering)

**关键问题**：token_history 每轮增长 → 填满上下文窗口 → 大部分历史无关紧要。

**解法**：将历史记录与 LLM 上下文**解耦**——`context = context_build(token_history, external_info)`。

具体技术：
- **工具切换**：动态更改可用工具集（编码→编辑→测试）
- **技能按需加载**：Skills = prompt + tools + instructions，只在需要时加载
- **压缩 (Compaction)**：编译日志只保留结果，训练曲线只保留loss
- **KV Cache 约束**：前缀不变 → KV Cache 永远命中（Manus 方案：masking 而非增删）
- **Ephemeral Context**：临时信息只用于当前决策，不存入历史

### 3. 虚假完成问题 (False Completion)

**核心发现**：~80% 的 Agent 失败来自虚假完成——Agent 自信地提交错误答案。

**Ralph Loop**：外循环启动干净上下文的 Agent 复查，消除确认偏差。

**Terminus-KIRA 变体**：Verifier 只看 actions+outputs（做了什么），不看 thoughts（怎么想的）。移除确认偏差但不需要完整重启。

### 4. 多 Agent / 子 Agent = 上下文隔离

多 Agent 的本质是**程序化的上下文隔离**，类似 OOP。同一个 Agent 既写代码又审代码 → reviewer 被 coder 思路影响（确认偏差）。解法：给每个角色一个干净上下文。

### 5. Test-Time Scaling (BTL 方案)

生成多个候选方案 → 用 pairwise comparison（Bradley-Terry-Luce 模型）选最优。避免 majority bias（当成功率 <50% 时，多数派是错的）。

Terminus-KIRA 从 76.2 → 81.3 (+5.1)。

### 6. Memory-Driven Self-Evolution (OpenClaw)

Agent 完成任务后更新自己的 prompts/memory → 跨任务持续学习。"更新 skill = 更新 prompt"。

### 7. 重要警告

> "Skills are also the easiest way to overfit an agent to a benchmark. Task-specific skills can inflate scores without improving general capability."

技能是最容易让 Agent 在基准测试上过拟合的方式。

---

## 8 项优化方案 × 设计思考

### A1: 交付反偏差验证（Ralph Loop 思想）

**论文依据**：§7 False Completion Problem + §7.2 Terminus-KIRA Approach

**问题分析**：
PI 现有的交付六令 + 自检三令专注于"做得对不对"（质量检查），但缺乏**对确认偏差的显式对抗**。Agent 修完 bug 后"自我感觉良好"是最常见的虚假完成来源。Ralph Loop 的洞见是：用干净上下文重新审视，或至少"只看事实不看推理过程"来验证。

**设计决策**：
- 不引入完整的 Ralph Loop（太重，消耗额外 API 调用）
- 采用 Terminus-KIRA 的轻量变体：在交付前要求"剥离推理，只看事实"重新验证
- 具体做法：在交付六令的证据门中增加"反偏差验证"步骤

**实现位置**：SKILL_META.md §8.6 交付六令·证据门

**新增内容**：
```
- **反偏差验证**（Ralph Loop 轻量版）：交付前重新审视——只看"做了什么"（代码diff/测试输出/命令结果），
  不回顾"怎么想的"（推理过程）。问自己：如果我是一个刚接手的新 Agent，只看到这些变更和输出，
  我会认为问题已解决吗？若有犹豫 → 补充验证
```

**预期影响**：verification_done ↑（减少虚假完成）

---

### A2: 信息分级指令（Ephemeral Context 思想）

**论文依据**：§4.5 Ephemeral Context + §4.3 Compaction

**问题分析**：
PUBG Ally 的做法：丰富的战况信息（敌人位置、血量、毒圈）对当前决策至关重要，但对未来迭代无用。区分"需要记住的"和"看完即弃的"可以大幅降低 token 消耗。

PI 的调试七步在多轮迭代中积累大量中间信息（编译日志、堆栈跟踪、grep 结果），但没有显式指导 Agent 区分哪些是临时的（用完即弃）、哪些是持久的（写入战域卡）。

**设计决策**：
- 在调试七步的"读败"步骤后增加信息分级指令
- 与战域卡的写入逻辑联动：只有"持久信息"才写入战域卡

**实现位置**：SKILL_META.md §4.1 调试七步·步一后

**新增内容**：
```
信息分级（调试过程中持续执行）：
- 临时信息（Ephemeral）：编译日志全文、grep 完整输出、堆栈跟踪详情 → 提取结论后丢弃原文，只保留"第42行 NPE"/"grep 发现3处同类"等结论
- 持久信息（Persistent）：根因定位、修复方案、已排除的假设、同类问题列表 → 写入战域卡/历史
- 判断标准：问"下一轮迭代还需要这段原文吗？" → 否 = 临时，是 = 持久
```

**预期影响**：多轮调试效率 ↑（减少 token 消耗），间接提升 steps_taken 质量

---

### A3: 审查反偏差令（Multi-Agent Context Isolation 思想）

**论文依据**：§5 Multi-Agents + §7.2 Terminus-KIRA

**问题分析**：
论文的核心洞见：如果同一个 Agent 既写代码又审代码，reviewer 被 coder 的思路影响（确认偏差）。Terminus-KIRA 的解法：verifier 只看 actions+outputs，不看 thoughts。

PI 的审码协议有四维扫描（安全/性能/可读/正确），但没有显式的**反确认偏差指令**。当 Agent 自己修完代码后做自审时，容易"自己觉得自己没问题"。

**设计决策**：
- 在审码协议中增加"反偏差审查"指令
- 要求审查时"假装不知道修复思路"，只看代码事实
- 自审与他审的反偏差策略不同：他审天然有隔离，自审需要显式指令

**实现位置**：SKILL_META.md §4.1 审码协议

**新增内容**：
```
反偏差审查（自审时强制·他审时推荐）：
审查代码时，剥离之前的推理和修复思路，只看代码事实：
1. 重读变更的代码，假设自己是首次看到这段代码的reviewer
2. 只根据代码本身判断正确性，不依赖"我知道我为什么这么改"的背景知识
3. 如果是自审（修复后验证），额外问："一个不知道bug原因的人，看到这段代码会发现什么问题？"
```

**预期影响**：hidden_issues ↑（自审时发现更多隐患）、verification_done 质量 ↑

---

### A4: 量化锚点（Progress-Measurable 思想）

**论文依据**：§8 AutoResearch

**问题分析**：
AutoResearch 不需要 Ralph Loop 的原因：任务有可量化的完成指标（val_loss 下降与否），虚假完成几乎不可能。

PI 的启动三查·查标定义了"必达/应达/可达"三档，但内容偏主观（"合理质量线"）。如果每个任务启动时都锚定到**可量化的指标**（测试通过数、编译错误数、覆盖率），交付时用数字证明进展，则虚假完成概率大幅降低。

**设计决策**：
- 在查标中增加"定锚"子步骤
- 要求每个任务识别可量化的完成指标
- 不强制所有任务都有量化指标（有些任务天然是定性的），但要求优先寻找

**实现位置**：SKILL_META.md §8.3 启动三查·查标

**新增内容**：
```
查标·定锚（优先寻找量化指标）：
- 优先锚定可量化指标：测试通过数(3/5→5/5)、编译错误数(12→0)、覆盖率(60%→80%)、响应时间(2s→200ms)
- 交付时用数字证明进展："{指标}从{修复前}→{修复后}"
- 无法量化时：锚定到可验证的行为描述（"curl 返回200"/"日志不再出现 ERROR"）
```

**预期影响**：verification_done ↑（量化验证更有说服力）

---

### A5: 前缀压缩去重（KV Cache 友好思想）

**论文依据**：§4.4 KV Cache Constraints

**问题分析**：
Manus 的做法是保持前缀稳定以最大化 KV Cache 命中。PI SKILL 作为系统提示本身是稳定前缀（KV Cache 友好），但内部存在跨章节重复内容。之前的分析发现 pi/SKILL.md 有 ~18-22% 冗余，约 700-1000 tokens 可以消除。

重复内容不影响 KV Cache 命中率（前缀仍然稳定），但增加了首次计算成本和 token 消耗。

**设计决策**：
- 这是编译层优化，在 COMPILER.md 中增加显式的去重规则
- 标记已知的重复项，编译时合并
- 不在 SKILL_META.md 中去重（META 允许详尽）

**实现位置**：COMPILER.md §标准版前置优化

**新增内容**：
```
已知跨章节重复（编译时合并到首次出现位置，后续引用改为交叉引用）：
- 验证矩阵：§4.1 定义 + §8.6 交付六令引用 → 只保留§4.1 定义，§8.6 引用为"按验证矩阵(§4.1)执行"
- 反模式戒律：§1.4 定义 + 证据门/调试七步多处引用 → 定义保持§1.4，引用处只写戒律编号
- 致人术三式：§3.2 定义 + 调试七步·扩圈/交付六令多处引用 → 定义保持§3.2，引用处交叉引用
```

**预期影响**：Faster（token 效率 ↑），首次加载成本 ↓

---

### A6: 经验沉淀指令（Memory-Driven Self-Evolution 思想）

**论文依据**：§11 OpenClaw: Self-Evolving Agents via Memory

**问题分析**：
OpenClaw 的核心创新：Agent 完成任务后更新自己的 prompts/memory → "通过内存实现任务间的连续性"。

PI 已有自演化协议（§8.4）和经验三域（战/鉴/道），但在善始善终（§8.5）的止损输出中缺乏**显式的经验沉淀步骤**。止损时的情报（已证/已排/收敛域）是最宝贵的学习材料，应强制沉淀。

**设计决策**：
- 在善始善终的5项输出后增加第6项：经验沉淀
- 与经验三域联动：止损情报 → 鉴域（跨任务可复用的教训）
- 不仅止损时沉淀，修复成功后也沉淀（与战后三省联动）

**实现位置**：SKILL_META.md §8.5 善始善终

**新增内容**：
```
6. 💎 **经验沉淀**——将本次调试/修复中发现的模式写入鉴域：
   - 有效策略 → "遇到{症状}时，{方法}有效"
   - 踩坑教训 → "遇到{场景}时，避免{做法}，因为{原因}"
   - 工具技巧 → "{工具}在{场景}下的最佳用法是{用法}"
```

**预期影响**：长期能力 ↑（跨会话知识积累）

---

### A7: 通用能力优先审计（Anti-Benchmark-Overfitting 思想）

**论文依据**：§4.2 Skills 中的警告

**问题分析**：
论文直接警告："Skills are the easiest way to overfit an agent to a benchmark. Task-specific skills can inflate scores without improving general capability."

PI 的 COMPILER.md Core 选择原理以"评测指标驱动"为核心（"每一行都必须直接驱动至少1个评测指标"），这有 benchmark overfitting 风险。需要确保 Core 中的能力是**通用的**（对真实任务也有效），而非仅为评测场景设计的 hack。

**设计决策**：
- 在 COMPILER.md 中增加"通用能力审计"约束
- Core 的每条规则必须同时满足两个条件：①驱动评测指标 ②对真实场景有效
- 定期审计：如果某条规则只在评测中生效、真实场景无效 → 降级到 references/

**实现位置**：COMPILER.md §渐进Core编译规则

**新增内容**：
```
**通用能力审计**（防 Benchmark Overfitting）：
- Core 每条规则必须同时满足：①驱动 ≥1 个评测指标 ②在真实编程/调试/审查场景中同样有效
- 审计信号：某条规则在评测中提分但真实场景中被用户跳过/忽略 → 降级到 references/
- 原则：通用能力 > 评测得分。评测是能力的**度量**，不是能力的**目标**
```

**预期影响**：Better（真实场景能力），防止过拟合

---

### A8: 方案对比令（Test-Time Scaling / BTL 思想）

**论文依据**：§10 Test-Time Scaling for Agents

**问题分析**：
论文发现：当成功率 <50% 时，majority voting 反而有害（多数派是错的）。BTL pairwise comparison 通过逐对比较避免 majority bias，Terminus-KIRA 从 76.2→81.3 (+5.1)。

PI 的"以正合以奇胜"要求新方案三条件（换道破局/可验可伪/败亦生谋），但没有**多方案并行对比选择**的显式指令。在深度调试（≥3阶）时，要求生成多个候选方案并逐对比较，可以提升解决率。

**设计决策**：
- 在失败升级的 🦈深搜（3次）阶增加"方案对比"要求
- 不要求 full BTL（太重），但要求至少生成 2-3 个本质不同的方案，逐对说明优劣
- 与致人术第四式·方案比选格式联动

**实现位置**：SKILL_META.md §5.1 六阶战势·🦈深搜阶

**新增内容**：
```
🦈深搜阶增强：生成 ≥2 个本质不同的候选方案 → 逐对比较优劣（不一次性比全部，避免 majority bias）→ 选择最优方案执行。
格式：致人术·方案比选(§3.2)。
```

**预期影响**：approach_changes ↑（更多策略切换）、解决率 ↑

---

## 实现清单

| 编号 | 优化项 | 修改文件 | 修改位置 | 状态 |
|------|--------|---------|---------|------|
| A1 | 交付反偏差验证 | SKILL_META.md | §8.6 交付六令·证据门 | ✅ |
| A2 | 信息分级指令 | SKILL_META.md | §4.1 调试七步 | ✅ |
| A3 | 审查反偏差令 | SKILL_META.md | §4.1 审码协议 | ✅ |
| A4 | 量化锚点 | SKILL_META.md | §8.3 启动三查·查标 | ✅ |
| A5 | 前缀压缩去重 | COMPILER.md | §标准版前置优化 | ✅ |
| A6 | 经验沉淀指令 | SKILL_META.md | §8.5 善始善终 | ✅ |
| A7 | 通用能力审计 | COMPILER.md | §渐进Core编译规则 | ✅ |
| A8 | 方案对比令 | SKILL_META.md | §5.1 六阶战势 | ✅ |

---

## 版本影响

- SKILL_META.md: v22 → v23（8项增强）
- COMPILER.md: 增加去重规则 + 通用能力审计约束
- 编译产物需重新生成：pi/SKILL.md, pi-en/SKILL.md, pi-progressive/SKILL.md, pi-en-progressive/SKILL.md

## 后续跟踪

- [ ] Round 2 benchmark 完成后对比 v22 baseline
- [ ] 重新编译 4 个 SKILL 变体
- [ ] 验证 A1-A8 是否传递到编译产物
- [ ] 下一轮 benchmark (Round 3) 验证 v23 提升效果
