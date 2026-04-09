# PI 智行合一引擎 — 深度分析与重构方案报告

> **分析者**: AI Agent (Claude)
> **日期**: 2026-04-09
> **版本**: 基于 PI v23 (SKILL.md) / v20 (README)

---

## 目录

- [第一部分：项目深度分析](#第一部分项目深度分析)
  - [1.1 黑盒视角：项目作用、输入与输出](#11-黑盒视角项目作用输入与输出)
  - [1.2 运作流程深度解析](#12-运作流程深度解析)
  - [1.3 架构设计分析](#13-架构设计分析)
  - [1.4 决策机制的实现细节](#14-决策机制的实现细节)
  - [1.5 可视化模块分析](#15-可视化模块分析)
  - [1.6 核心价值评估](#16-核心价值评估)
- [第二部分：逻辑问题与风险识别](#第二部分逻辑问题与风险识别)
  - [2.1 设计中的逻辑问题](#21-设计中的逻辑问题)
  - [2.2 重大风险项](#22-重大风险项)
- [第三部分：重构方案 — 上下文滑动编辑器](#第三部分重构方案--上下文滑动编辑器)
  - [3.1 核心理念](#31-核心理念)
  - [3.2 架构设计](#32-架构设计)
  - [3.3 关键模块详解](#33-关键模块详解)
  - [3.4 失败因素分析与对策](#34-失败因素分析与对策)
  - [3.5 实施路线图](#35-实施路线图)
- [结论](#结论)

---

## 第一部分：项目深度分析

### 1.1 黑盒视角：项目作用、输入与输出

#### 项目定位

PI（智行合一引擎）是一套**面向 AI 编程助手的元认知增强系统（Meta-Cognitive Enhancement System）**。它不是代码、不是应用程序，而是一套**纯文本协议**（Prompt Engineering Framework），通过注入 System Prompt 的方式改变 AI 编程助手的行为模式。

#### 输入

| 输入类型 | 具体内容 | 形式 |
|---------|---------|------|
| **核心输入** | SKILL.md（~1090行 Prompt 指令集） | Markdown 纯文本 |
| **用户意图** | 用户在 AI 编程助手中的自然语言请求 | 对话消息 |
| **代码上下文** | 用户当前工作的代码仓库 | 文件系统 |
| **平台环境** | 宿主平台（Claude Code / Cursor / Kiro 等 13+ 平台） | 平台 API |

#### 输出

| 输出类型 | 具体内容 | 形式 |
|---------|---------|------|
| **行为改变** | AI 按照九大场景、六大认知原型等框架执行 | 对话行为 |
| **结构化思维** | 场景公示、明链、明证、明树等可见输出 | 格式化文本 |
| **决策日志** | 决策历史记录（通过 hooks 采集） | JSONL 文件 |
| **可视化面板** | 决策树/时间线的交互式页面 | Web 应用 |
| **评测报告** | PI vs PUA vs NoPUA 对比 benchmark | HTML 报告 |

#### 本质

```
用户的编程请求 + PI 协议注入 → AI 的高质量结构化行为输出
```

PI 本质上是一个**LLM 行为编译器**：将人类编程方法论（东方哲学 + 西方方法论 + MBTI 认知理论）编译为 LLM 可执行的行为指令。

---

### 1.2 运作流程深度解析

#### 1.2.1 生产流水线（P1→P4）

PI 有一条清晰的四阶段生产流水线：

```
P1·迭代 ──→ P2·编译 ──→ P2.5·Eval ──→ P3·分发 ──→ P4·翻译
  │           │            │            │           │
SKILL_META  SKILL.md    ≥8/9场景     6平台版本    英文版
(~1185行)   (~950行)     通过率       统一body
```

**P1·迭代**：使用 `iterate.md` 审计协议对 SKILL_META.md 进行增量修改。五维十四检 + 九大逻辑链确保修改不引入矛盾。校验门禁：P0/P1 问题归零。

**P2·编译**：COMPILER.md 将完整版压缩为精简版。核心决策树：
- AI 读到后会改变 token 生成？→ 保留
- 是认知处理策略？→ 保留
- 是格式化输出模板？→ 保留
- 是古典引语/思想源？→ 剥离

**P2.5·Eval**：使用 benchmark/local_run.py 在 9 个场景上跑分。8 个指标维度（issues_found, hidden_issues, verification_done 等），≥8/9 场景通过方可进入 P3。

**P3·分发**：将 SKILL.md 适配到 13+ 平台的不同 frontmatter 格式。PURGE 裁剪特定平台不需要的段落（如 Copilot CLI 保留 Loop，其他平台裁剪）。

**P4·翻译**：中文→英文，行为等价校验。

#### 1.2.2 运行时行为流程

当用户在 AI 编程助手中发出请求时，PI 的运行时流程为：

```
用户请求
   │
   ▼
┌─────────────────────┐
│ 参数快捷路由判定      │  ← /pi 编程 深度 等参数直接路由
│ (§参数快捷路由)       │
└─────────┬───────────┘
          │ 无参数
          ▼
┌─────────────────────┐
│ 启动三查             │  ← 查境(环境)→查史(历史)→查标(验收标准)
│ (§8.3)              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 难度自适应判定        │  ← 标准 / 深度（调试即深度）
│ (§8.2)              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 场景路由              │  ← 关键词匹配→九大场景之一
│ (§1.3)              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 认知阵激活            │  ← MBTI 认知原型组合
│ (§1.2)              │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 场景公示输出          │  ← 🧠 PI · {场景} · {认知阵} · ⚡{难度}
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 四道合一执行          │  ← 编程/测试/产品/运营 四令+三则
│ (§4.1-4.4)          │
└─────────┬───────────┘
          │
     ┌────┴────┐
     │ 失败？   │
     │  Y    N  │
     └─┬────┬──┘
       │    │
       ▼    ▼
   ┌───────┐ ┌──────────┐
   │六阶战势│ │交付六令   │
   │(§5.1) │ │(§8.6)   │
   └───┬───┘ └──────────┘
       │
       ▼
   ┌───────────────┐
   │止损三阶 并行    │  ← 预警→止损→善始善终
   │(§8.2)         │
   └───────────────┘
```

---

### 1.3 架构设计分析

#### 1.3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        PI 引擎架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 元认知层      │  │ 方法体系层    │  │ 行为控制层            │   │
│  │              │  │              │  │                      │   │
│  │ · 六大认知原型 │  │ · 五略       │  │ · 反模式十一戒        │   │
│  │ · 十六源智慧  │  │ · 致人术四式  │  │ · 强制令五敕          │   │
│  │ · 九大场景    │  │ · 九令洞鉴    │  │ · 交付六令            │   │
│  │ · 认知五阵    │  │ · 天行飞轮    │  │ · 自检三令            │   │
│  │              │  │ · 已试策略簿  │  │ · 验证矩阵            │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                      │               │
│         ▼                 ▼                      ▼               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    动态响应层                               │   │
│  │  · 六阶战势（失败升级）  · 止损三阶（资源感知）               │   │
│  │  · 肃阵语气层           · 截教一线生机                       │   │
│  │  · 十二灵兽图腾          · 失败→对策统一决策表               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    人机共振层                               │   │
│  │  · 共振五式（明链/明证/明树/明心/明约）                       │   │
│  │  · 三档自治度   · 信息判别   · 交互三问                       │   │
│  │  · 渐进式交付   · 上下文恢复   · 自演化协议                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    团队协作层                               │   │
│  │  · Leader/Teammate/Coach 三角色                             │   │
│  │  · 决策三权   · 汇报协议   · Coach 巡检                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    基础设施层                               │   │
│  │  · Hooks 数据采集   · 可视化面板   · Benchmark 评测         │   │
│  │  · install.sh       · 多平台分发   · 渐进式加载             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3.2 设计模式识别

| 设计模式 | 在 PI 中的体现 | 实现方式 |
|---------|---------------|---------|
| **状态机** | 六阶战势（失败计数驱动状态转换） | 文本描述的状态转换表 |
| **策略模式** | 六大认知原型按场景切换 | 认知栈参数集 |
| **责任链** | 九令洞鉴渐进激活 | 按失败阶数逐步启用令 |
| **观察者** | Hooks 事件采集系统 | Shell 脚本 + JSONL |
| **路由器** | 场景路由（关键词→场景映射） | 查表匹配 |
| **编译器** | P2 阶段 SKILL_META→SKILL | 保留/剥离决策树 |
| **门禁（Gate）** | 各阶段校验门禁 | 条件检查清单 |

---

### 1.4 决策机制的实现细节

#### 1.4.1 场景路由决策

**实现方式**：关键词→场景查表。

```
输入关键词: "代码/架构/API/实现"  →  🖥️ 编程开发
输入关键词: "报错/异常/崩溃/超时"  →  🔧 调试排障
```

**问题**：这是纯文本描述，无运行时代码执行。决策完全依赖 LLM 的指令遵循能力。

#### 1.4.2 难度自适应决策

```
if 涉及(报错/异常/bug修复/代码审查/排障):
    → 🐲深度模式（调试即深度，无例外）
elif 常规编码/新功能/配置/重构:
    → 🏋️标准模式
elif 🏋️标准连续失败2次:
    → 强制升级🐲深度 + 战势二阶
```

#### 1.4.3 战势升级决策

这是 PI 最核心的决策链，一个**失败次数驱动的状态机**：

```
失败次数  →  阶位      →  策略切换            →  核心动效
   2      →  ⚡易辙    →  建筑师切换视角       →  换道 + 九令五六九
   3      →  🦈深搜    →  分析师穷源竟委       →  穷搜 + 方案对比 + 九令七八
   4      →  🐲系统    →  统帅庙算全局         →  九令尽行 + 三策另立
   5      →  🦁决死    →  探索者全新路线       →  最小实证 + 隔离
   6      →  ☯️截道    →  全原型截取一线       →  逆向/跨域/降维
   7+     →  🐝天行    →  全原型协同出击       →  穷尽后体面移交
```

#### 1.4.4 止损决策（与战势并行）

```
🟢正常  ──→  🟡预警(失败3+次/九令≥5)  ──→  🔴止损(九令完成仍未解)
              ↓                              ↓
          告知消耗，建议是否继续           善始善终五件输出
```

**关键设计**：战势管升级（越挫越勇），止损管降级（量入为出）。两套机制并行运行，互不替代。

#### 1.4.5 反模式检测决策

十一条反模式戒律形成负面约束空间：

```
猜而不搜 → 搜→读→验→再断
改而不验 → 即改即验附输出
重而不换 → 换道破局
停而不追 → 同类排查+关联预判
...
窄而不阔 → 隐患≥表面问题40%
```

---

### 1.5 可视化模块分析

#### 输入

| 输入 | 来源 | 格式 |
|------|------|------|
| 决策事件 | Hooks 采集（hooks.json 配置） | JSONL |
| Session 元数据 | capture-decision.sh | JSON |
| 工具结果 | capture-tool-result.sh | 事件记录 |
| SubAgent 事件 | capture-subagent.sh | 事件记录 |
| 用户 Prompt | capture-prompt.sh | 事件记录 |

#### 数据流

```
AI 编程助手运行
     │
     ├── UserPromptSubmit  → capture-prompt.sh   → ~/.pi/decisions/{date}/session.events.jsonl
     ├── Stop              → capture-decision.sh → ~/.pi/decisions/{date}/session.events.jsonl
     ├── PostToolUse       → capture-tool-result.sh → events
     ├── PreCompact        → pre-compact.sh      → 注入恢复协议
     └── SubagentStart/Stop → capture-subagent.sh → events
                                        │
                                        ▼
                              ┌─────────────────┐
                              │ Visualize Server  │
                              │ (Node.js+Express) │
                              │ + WebSocket       │
                              │ + chokidar        │
                              └────────┬──────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ React Flow UI    │
                              │ 决策图 + 时间线   │
                              │ + 详情面板        │
                              └─────────────────┘
```

#### 输出

- 交互式决策图（React Flow 驱动，拖拽/缩放）
- 时间线回放滑块
- Session 树导航（按日期分组）
- 实时 WebSocket 更新
- 导出/导入（隐私脱敏）

#### 技术栈

React 19 + TypeScript 5.7 + Vite 6 + Tailwind CSS + React Flow 12 + Zustand 5 + Express + WebSocket + chokidar

---

### 1.6 核心价值评估

#### 创新点

1. **元认知框架化**：将编程方法论从隐性知识转化为可注入 LLM 的显式指令，这是 prompt engineering 领域的系统性工程
2. **失败升级状态机**：六阶战势是一个设计精巧的渐进式应急响应系统，对标工业界的 Incident Response Level
3. **多平台统一分发**：一套核心协议适配 13+ 平台，是目前最广泛的 AI Skill 分发方案
4. **Eval 驱动迭代**：benchmark 闭环验证，用数据证明 prompt 工程有效性
5. **东西方融合表达**：用东方哲学的直觉性表达包装西方工程方法论，利用 LLM 对隐喻的理解能力

#### 局限

1. **纯文本协议**的固有脆弱性——所有行为依赖 LLM 的指令遵循概率
2. **一次性全量加载**的 token 消耗——1090 行 SKILL 即使渐进式也需 410 行核心
3. **无运行时状态持久化**——战势、策略簿等状态完全寄存于 LLM 的 context window
4. **benchmark 自评测偏差**——使用 LLM 提取指标评估 LLM 输出，存在评测者-被评者同源问题

---

## 第二部分：逻辑问题与风险识别

### 2.1 设计中的逻辑问题

#### 问题 1：指令膨胀与遵循率的倒 U 曲线

**症状**：SKILL.md 1090 行包含数百条指令（11 条戒律 + 5 条强制令 + 7 步调试 + 4 式致人术 + 9 令洞鉴 + 6 阶战势 + 5 式共振 + 6 令交付 + 3 令自检 + ...），总指令数估计 **80-120 条**。

**逻辑问题**：LLM 对 system prompt 指令的遵循率随指令数量增加呈**倒 U 曲线**：
- 少量指令（<20条）：高遵循率（>90%）
- 中等指令（20-50条）：中等遵循率（~70%）
- 大量指令（80+条）：遵循率急剧下降，出现**指令竞争**和**选择性遗忘**

PI 的 benchmark 数据也印证了这一点：某些场景的 `self_corrections` 和 `approach_changes` 指标存在"地板风险"（min=1），说明 LLM 并非总能执行所有要求。

#### 问题 2：战势状态机的无状态悖论

**症状**：六阶战势依赖"失败次数"驱动状态转换，但 LLM 没有持久化的计数器。

**逻辑问题**：
- 失败次数由 LLM 在 context window 中"记忆"
- Context window 压缩（compact）后，失败计数可能丢失
- PreCompact hook 注入恢复协议，但恢复快照本身也是文本，LLM 可能不准确恢复
- **结果**：在长对话中，战势可能被重置、跳阶或卡死

#### 问题 3：认知原型的伪个性化

**症状**：六大认知原型（INTJ/ENTJ/ENFP/ISTJ/INFJ/INTP）被描述为"信息处理优先级参数集"。

**逻辑问题**：
- LLM 无法真正"切换"认知栈——`Ni→Te→Fi→Se` 对 LLM 来说只是一组 token
- 不同认知原型产生的行为差异可能 **≤ 噪声水平**
- benchmark 未单独评估不同认知原型的效果差异
- **风险**：这可能是一个 **安慰剂效应**——用户感知到了差异，但实际输出无显著区别

#### 问题 4：评测中的古德哈特定律

**症状**：eval_criteria.md 定义了 8 个具体指标（如 issues_found ≥ 3, hidden_issues ≥ 2），SKILL.md 的修改被这些指标驱动。

**逻辑问题**：
- 古德哈特定律："当一个指标变成目标时，它就不再是好的指标"
- SKILL.md 中直接要求"隐患数量 ≥ 表面问题的 40%"，这不是在提升真实能力，而是在 **教 LLM 凑数**
- benchmark 提取器（qodercli/claude）使用极宽松的评判标准（如 "be VERY generous" for verification_done），降低了评测辨别力
- **结果**：PI 在 benchmark 上的领先可能部分来自 **指标过拟合** 而非真实能力提升

#### 问题 5：场景路由的脆弱匹配

**症状**：场景路由基于关键词匹配（"代码/架构/API/实现" → 编程开发）。

**逻辑问题**：
- 现实用户请求常常**跨场景**："帮我调试这个 API 的性能问题并给出重构方案"（调试+编程+产品）
- 关键词匹配无法处理意图模糊的情况
- 场景切换公示增加了对话噪音
- **没有机制**处理用户在同一轮对话中频繁切换场景的情况

#### 问题 6：灵兽/哲学包装的认知负荷

**症状**：十二灵兽、十六源智慧、截教一线生机、捭阖之术等包装。

**逻辑问题**：
- 对 LLM 而言，"🦈鲨→搜索/潜搜" 与 "进行广度和深度搜索" **语义等价**
- 但前者引入了 **额外的映射解码成本**——LLM 需要先理解"鲨=搜索"再执行
- 这些包装增加了 SKILL.md 的体积（~15-20% token 用于哲学/灵兽包装）
- **价值争议**：对用户有情绪价值和仪式感，但对 LLM 执行效率可能有负面影响

---

### 2.2 重大风险项

#### 风险 1：LLM 版本升级导致行为漂移（概率：高，影响：致命）

PI 的所有行为指令都是 **软约束**。当 Claude/GPT/Gemini 模型升级时：
- 指令遵循的优先级可能重排
- 某些格式化输出可能被模型的新训练数据覆盖
- 已验证的 benchmark 结果可能瞬间失效

**当前应对**：仅有 benchmark 回归测试。但 benchmark 本身依赖 LLM 提取，形成脆弱循环。

#### 风险 2：Token 经济学不可持续（概率：高，影响：中）

| 内容 | Token 估计 |
|------|-----------|
| SKILL.md 全量加载 | ~15,000-20,000 tokens |
| 渐进式核心加载 | ~6,000-8,000 tokens |
| 每次场景公示+明链 | ~200-500 tokens |
| 战势/情报输出 | ~300-800 tokens |

在一次中等复杂的调试任务中，PI 框架本身可能消耗 **20,000-30,000 tokens**，占总 context 的 15-25%。这些 token 用于框架而非用户任务。

#### 风险 3：多平台一致性维护成本爆炸（概率：中，影响：高）

- 13+ 平台 × 2 语言 × 2 版本（完整/渐进） = **52+ 文件** 需要同步
- 任何一次 SKILL.md 修改都触发完整的 P2→P3→P4 流水线
- 人工校验 "body 一致" + "description 一致" 的工作量线性增长

#### 风险 4：Benchmark 的统计效力不足（概率：高，影响：中）

- 每场景仅 2 runs
- 使用 LLM 自动提取指标（提取一致性未经验证）
- 3 条件（PI/PUA/NoPUA）× 9 场景 × 2 runs = 仅 54 个数据点
- Mann-Whitney U 检验在如此小的样本量下统计效力很低

#### 风险 5：Hooks 安全与隐私（概率：中，影响：高）

- capture-decision.sh 记录用户的完整代码上下文
- capture-prompt.sh 记录用户的所有输入
- 数据存储在 `~/.pi/decisions/` 无加密
- 导出功能声称"隐私脱敏"，但脱敏逻辑是否全面未经审计

---

## 第三部分：重构方案 — 上下文滑动编辑器

### 3.1 核心理念

**问题本质**：当前 PI 是一个**静态文档**——1090 行全量注入，然后祈祷 LLM 在正确的时刻执行正确的指令。这就像给一个人一本 1000 页的操作手册，然后要求他在工作中随时翻到正确的页面。

**解决方案**：构建一个**上下文滑动编辑器（Context Sliding Editor, CSE）**——一个动态的 Prompt 编排系统，在运行时根据当前状态精确地控制 LLM 的 context window 内容。

```
           ┌──────────────────────────────────────────────┐
           │        上下文滑动编辑器 (CSE)                   │
           │                                              │
           │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
           │  │锚点│ │场景│ │战势│ │工具│ │交付│  ← 指令块  │
           │  │ 5令│ │编程│ │二阶│ │调试│ │六令│           │
           │  └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘        │
           │     │      │      │      │      │           │
           │     ▼      ▼      ▼      ▼      ▼           │
           │  ═══════════════════════════════════════      │
           │  │  当前滑动窗口（动态组装的 Context）    │      │
           │  ═══════════════════════════════════════      │
           │                                              │
           │  Token 预算: 3000/5000  ████████░░          │
           └──────────────────────────────────────────────┘
```

**类比**：如果说当前的 PI 是一本"操作手册"，CSE 就是一个"GPS 导航仪"——只在需要的时刻提供需要的指令。

### 3.2 架构设计

#### 3.2.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CSE (Context Sliding Editor) 架构                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                   │
│  │ 指令块仓库    │  ← 原子化的指令片段，每个 100-300 tokens           │
│  │ (Block Store) │                                                   │
│  │              │  blocks/                                          │
│  │  anchor.md   │  ├── anchor.md      (强制令5条, ~200 tokens)      │
│  │  dev.md      │  ├── scenes/                                     │
│  │  debug.md    │  │   ├── dev.md     (编程四令, ~300 tokens)       │
│  │  review.md   │  │   ├── debug.md   (调试七步, ~400 tokens)      │
│  │  ...         │  │   ├── review.md  (审码协议, ~300 tokens)       │
│  │              │  │   └── ...                                     │
│  └──────┬───────┘  ├── tactics/                                    │
│         │          │   ├── escalation.md (战势, ~300 tokens)        │
│         │          │   ├── search.md    (致人术, ~200 tokens)       │
│         │          │   └── ...                                     │
│         │          ├── delivery/                                    │
│         │          │   ├── checklist.md (交付六令, ~200 tokens)     │
│         │          │   └── format.md   (输出格式, ~150 tokens)      │
│         │          └── meta.md         (block 索引+依赖图)          │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 状态追踪器    │  ← 持久化的运行时状态（非 LLM 内存）               │
│  │ (State       │                                                   │
│  │  Tracker)    │  state.json:                                     │
│  │              │  {                                                │
│  │              │    "scene": "debug",                              │
│  │              │    "difficulty": "deep",                          │
│  │              │    "failure_count": 3,                            │
│  │              │    "escalation_level": 2,                         │
│  │              │    "tried_strategies": [...],                     │
│  │              │    "active_blocks": ["anchor","debug","escalation"]│
│  │              │    "token_budget": 5000,                          │
│  │              │    "token_used": 2800                             │
│  │              │  }                                                │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 滑动编排器    │  ← 核心引擎：根据状态动态组装 context              │
│  │ (Slider      │                                                   │
│  │  Composer)   │  输入: 用户消息 + 当前状态 + 指令块仓库             │
│  │              │  输出: 组装后的 system prompt                       │
│  │              │                                                   │
│  │  算法:                                                           │
│  │  1. 锚点块（永驻）                                                │
│  │  2. 场景块（按当前场景选择）                                       │
│  │  3. 战术块（按失败次数/难度选择）                                   │
│  │  4. 交付块（接近交付时注入）                                       │
│  │  5. Token 预算约束                                                │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Hook 集成层   │  ← 利用宿主平台的 hook 机制                       │
│  │ (Platform    │                                                   │
│  │  Adapter)    │  · Claude Code: hooks.json                       │
│  │              │  · Cursor: .cursor/rules/ 动态更新                │
│  │              │  · 其他平台: 适配器                                 │
│  └──────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 指令块设计

每个指令块是一个原子化的 Markdown 文件，带有元数据头：

```yaml
---
id: debug-7step
category: scene
scene: debug
priority: 1          # 1=必须, 2=推荐, 3=可选
token_cost: 400
depends_on: [anchor]
conflicts_with: []
activation:
  - condition: "scene == debug"
  - condition: "difficulty == deep"
deactivation:
  - condition: "scene != debug"
version: 1
---

# 调试七步

| 步 | 敕令 | 动效 |
|----|-----|------|
| 一 | 读败 | 一字不漏读尽败报... |
...
```

**设计原则**：
- 每个块 **≤ 500 tokens**
- 块之间通过 `depends_on` 声明依赖关系
- `activation` 定义何时自动加载
- `conflicts_with` 防止互斥块同时加载

#### 3.2.3 滑动编排算法

```python
def compose_context(user_message: str, state: State, blocks: BlockStore) -> str:
    """核心编排算法：在 token 预算内组装最优 context"""
    
    budget = state.token_budget  # 例如 5000 tokens
    selected = []
    used = 0
    
    # Phase 1: 锚点块（永驻，不可跳过）
    anchor = blocks.get("anchor")
    selected.append(anchor)
    used += anchor.token_cost
    
    # Phase 2: 场景检测与路由
    scene = detect_scene(user_message, state)
    state.scene = scene
    
    # Phase 3: 按优先级加载场景块
    scene_blocks = blocks.query(category="scene", scene=scene)
    for block in sorted(scene_blocks, key=lambda b: b.priority):
        if used + block.token_cost <= budget:
            if not any(b.id in block.conflicts_with for b in selected):
                selected.append(block)
                used += block.token_cost
    
    # Phase 4: 战术块（根据状态动态选择）
    if state.failure_count >= 2:
        escalation = blocks.get(f"escalation-L{state.escalation_level}")
        if used + escalation.token_cost <= budget:
            selected.append(escalation)
            used += escalation.token_cost
    
    # Phase 5: 状态注入（非块，而是动态生成的状态摘要）
    state_summary = generate_state_summary(state)
    selected.append(state_summary)
    used += estimate_tokens(state_summary)
    
    # Phase 6: 交付块（检测到交付意图时注入）
    if detect_delivery_intent(user_message):
        delivery = blocks.get("delivery-checklist")
        if used + delivery.token_cost <= budget:
            selected.append(delivery)
            used += delivery.token_cost
    
    # Phase 7: 预算溢出处理
    if used > budget:
        selected = trim_to_budget(selected, budget)
    
    # 组装最终 prompt
    return assemble_prompt(selected, state)


def generate_state_summary(state: State) -> str:
    """动态生成状态摘要，替代 LLM 自行记忆"""
    return f"""
## 当前状态
- 场景: {state.scene} | 难度: {state.difficulty}
- 失败: {state.failure_count}次 | 战势: L{state.escalation_level}
- 已试策略: {', '.join(state.tried_strategies[-5:])}  # 只保留最近5条
- Token 预算: {state.token_used}/{state.token_budget}
"""
```

#### 3.2.4 状态追踪器设计

```python
@dataclass
class State:
    """持久化的运行时状态"""
    session_id: str
    scene: str = "unknown"
    difficulty: str = "standard"     # standard | deep
    failure_count: int = 0
    escalation_level: int = 0        # 0-6
    tried_strategies: list[str] = field(default_factory=list)
    active_blocks: list[str] = field(default_factory=list)
    token_budget: int = 5000
    token_used: int = 0
    delivery_pending: bool = False
    last_tool_result: str = ""       # success | failure
    context_version: int = 0         # 每次 context 变化递增
    
    def on_failure(self):
        """失败事件处理"""
        self.failure_count += 1
        if self.failure_count >= 2:
            self.escalation_level = min(self.failure_count - 1, 6)
        self.save()
    
    def on_success(self):
        """成功事件处理"""
        self.delivery_pending = True
        self.save()
    
    def save(self):
        """持久化到 ~/.pi/state/{session_id}.json"""
        path = Path.home() / ".pi" / "state" / f"{self.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
    
    @classmethod
    def load(cls, session_id: str) -> "State":
        path = Path.home() / ".pi" / "state" / f"{session_id}.json"
        if path.exists():
            return cls(**json.loads(path.read_text()))
        return cls(session_id=session_id)
```

### 3.3 关键模块详解

#### 3.3.1 场景检测器（替代关键词查表）

```python
# 使用轻量级分类而非硬关键词匹配
SCENE_SIGNALS = {
    "debug": {
        "keywords": ["error", "bug", "fix", "crash", "timeout", "报错", "异常"],
        "patterns": [r"traceback", r"error:", r"failed", r"exception"],
        "context_signals": ["failure_count > 0", "last_tool_result == failure"],
        "weight": 1.0
    },
    "dev": {
        "keywords": ["implement", "add", "create", "build", "代码", "实现", "开发"],
        "patterns": [r"function|class|module|api"],
        "context_signals": [],
        "weight": 0.8
    },
    # ...
}

def detect_scene(message: str, state: State) -> str:
    """多信号融合的场景检测"""
    scores = {}
    for scene, signals in SCENE_SIGNALS.items():
        score = 0
        # 关键词匹配
        score += sum(1 for kw in signals["keywords"] if kw in message.lower()) * 0.3
        # 正则匹配
        score += sum(1 for p in signals["patterns"] if re.search(p, message, re.I)) * 0.3
        # 上下文信号（来自持久化状态）
        for ctx in signals["context_signals"]:
            if eval_context_signal(ctx, state):
                score += 0.4
        scores[scene] = score * signals["weight"]
    
    best = max(scores, key=scores.get)
    return best if scores[best] > 0.3 else state.scene  # 低于阈值保持不变
```

#### 3.3.2 Token 预算管理器

```python
class TokenBudgetManager:
    """确保 PI 框架不超过 context window 的指定比例"""
    
    def __init__(self, max_ratio: float = 0.15):
        """
        max_ratio: PI 框架可占用的最大 context 比例
        例如 0.15 = 最多使用 15% 的 context window
        """
        self.max_ratio = max_ratio
    
    def calculate_budget(self, model_context_size: int, user_context_used: int) -> int:
        """动态计算当前可用 token 预算"""
        available = model_context_size - user_context_used
        pi_budget = int(available * self.max_ratio)
        return max(pi_budget, 1000)  # 最低保证 1000 tokens
    
    def prioritize_blocks(self, blocks: list, budget: int) -> list:
        """在预算约束下选择最高价值的指令块组合"""
        # 背包问题变体：priority 越小越重要
        blocks_sorted = sorted(blocks, key=lambda b: (b.priority, -b.token_cost))
        selected = []
        used = 0
        for block in blocks_sorted:
            if used + block.token_cost <= budget:
                selected.append(block)
                used += block.token_cost
        return selected
```

#### 3.3.3 平台适配器

```python
class PlatformAdapter:
    """统一不同平台的 hook 机制"""
    
    @staticmethod
    def for_claude_code() -> "ClaudeCodeAdapter":
        """利用 Claude Code 的 hooks.json 机制"""
        return ClaudeCodeAdapter()
    
    @staticmethod
    def for_cursor() -> "CursorAdapter":
        """利用 Cursor 的 .cursor/rules/ 动态更新"""
        return CursorAdapter()
    
    @staticmethod
    def for_generic() -> "GenericAdapter":
        """通用适配器：通过 PreCompact/Stop hook 注入"""
        return GenericAdapter()


class ClaudeCodeAdapter(PlatformAdapter):
    """Claude Code 适配器：利用 hooks 生命周期"""
    
    def inject_context(self, composed_prompt: str):
        """通过 UserPromptSubmit hook 注入动态 context"""
        # hook 返回 systemMessage 注入
        return {
            "systemMessage": composed_prompt
        }
    
    def on_tool_result(self, result: str, success: bool, state: State):
        """PostToolUse/PostToolUseFailure 时更新状态"""
        state.last_tool_result = "success" if success else "failure"
        if not success:
            state.on_failure()
        state.save()
```

#### 3.3.4 指令块的降噪重写

当前 SKILL.md 中的指令块重写示例：

**Before（当前 PI）**：
```markdown
### 5.2 截教·一线生机

> **大道五十，天衍四十九，截取其中一线生机。**

前四阶正道穷尽，截道阶启用截教——有教无类，万法皆可。

**截前一步·最小实证**：正道穷尽前，先退到最小能成功的一步验证之。
最小成功重建势头，再由此向外扩展。此乃"以退为进"——退一步海阔天空。

**截道三法**：逆向截取（反转核心假设） · 跨域截取（跨领域类比） · 降维截取（最原始方式验证）

**约束**：法家（法不阿贵）为边界，防止妄截导致幻觉。截教是核选项，非日常武器。

触发输出：`☯️ PI · 截教 · {逆向/跨域/降维} · ⚠️ {边界}`
```

**After（CSE 指令块）**：
```markdown
---
id: tactic-lastresort
category: tactic
priority: 3
token_cost: 120
activation:
  - condition: "escalation_level >= 5"
---

## 极限突破策略

当所有常规方案穷尽后（失败≥6次）：

1. **逆向验证**：反转你的核心假设，检验其反面
2. **跨域类比**：从其他技术领域寻找类似问题的解法
3. **降维实证**：用最原始的方式（print/curl/手动）验证最小假设

⚠️ 约束：保持事实依据，不引入未经验证的假设。
```

**降噪效果**：200+ tokens → 120 tokens，行为指令不变，去除哲学包装。

### 3.4 失败因素分析与对策

#### 失败因素 1：平台 Hook 能力不足

**风险**：并非所有平台都支持 `UserPromptSubmit` 这样的 hook 来注入动态 system prompt。Cursor 无 hook 机制，Kiro 仅有 `inclusion: auto`。

**对策**：
- **三级适配策略**：
  1. **全动态**（Claude Code）：利用 hooks 实现完整 CSE
  2. **半动态**（Cursor）：通过 `.cursor/rules/` 文件的 `alwaysApply` + 条件规则实现部分滑动
  3. **静态降级**（Kiro/其他）：退回渐进式加载，但使用 CSE 优化过的块结构
- **设计原则**：CSE 即使在无 hook 的平台上也不比当前 PI 差

#### 失败因素 2：状态追踪的准确性

**风险**：`failure_count` 的递增依赖 hook 捕获 `PostToolUseFailure`，但不是所有失败都通过工具失败体现。LLM 可能产生错误答案但工具调用成功。

**对策**：
- **双通道检测**：
  1. 工具结果通道：PostToolUse/PostToolUseFailure → 自动更新
  2. LLM 自报通道：在每个指令块中保留 `如果本次尝试失败，输出 "📉失败"` 的标记，Hook 通过 Stop 事件正则匹配 `📉失败` 更新计数
- **容错设计**：状态丢失时默认标准模式，不会比当前方案更差

#### 失败因素 3：指令块粒度的平衡

**风险**：块太细（<50 tokens）→ 失去上下文连贯性；块太粗（>500 tokens）→ 失去滑动灵活性。

**对策**：
- **标准粒度**：一个完整的行为协议 = 一个块（如"调试七步"是一个块，不拆成 7 个块）
- **目标**：80% 的块在 150-400 tokens 之间
- **允许例外**：锚点块（强制令）可以更小（~200 tokens），复杂调试协议可以更大（~500 tokens）

#### 失败因素 4：场景检测误判

**风险**：用户说"帮我看看这段代码"——可能是审查（review）也可能是理解（explain）。误判导致加载错误的指令块。

**对策**：
- **默认保守**：无法确定时加载通用块，不加载场景专属块
- **显式覆盖**：用户可通过 `/pi debug` 直接指定（保留当前参数快捷路由）
- **延迟加载**：第一轮对话只加载锚点+场景块，第二轮根据 LLM 的实际行为追加战术块

#### 失败因素 5：CSE 本身的复杂度

**风险**：CSE 引入了新的代码（Python/Node.js），而当前 PI 是纯文本。新代码意味着新 bug。

**对策**：
- **最小实现**：CSE 核心代码控制在 <500 行 Python
- **纯 Shell 适配**：对于只有 Shell hook 的平台，CSE 可以退化为一组 `cat blocks/*.md | head -c TOKEN_BUDGET` 的 Shell 脚本
- **渐进引入**：先在 Claude Code 上实现完整版，验证后再扩展

### 3.5 实施路线图

#### Phase 0：块化重写（2 周）

**目标**：将 SKILL.md 拆解为原子化指令块，不改变任何行为。

```
milestone-0/
├── blocks/
│   ├── anchor.md                (五敕令, ~200 tokens)
│   ├── anti-patterns.md         (十一戒, ~300 tokens)
│   ├── scenes/
│   │   ├── dev.md               (编程四令+正名三则, ~350 tokens)
│   │   ├── debug.md             (调试七步+前置搜索, ~450 tokens)
│   │   ├── review.md            (审码协议, ~300 tokens)
│   │   ├── test.md              (测试四令, ~250 tokens)
│   │   ├── product.md           (产品四令, ~250 tokens)
│   │   └── ops.md               (运营四令, ~250 tokens)
│   ├── tactics/
│   │   ├── escalation-L1.md     (易辙, ~150 tokens)
│   │   ├── escalation-L2.md     (深搜, ~200 tokens)
│   │   ├── escalation-L3.md     (系统, ~200 tokens)
│   │   ├── escalation-L4+.md    (决死+截道+天行, ~300 tokens)
│   │   ├── search-tactics.md    (致人术, ~250 tokens)
│   │   └── tried-log.md         (已试策略簿, ~100 tokens)
│   ├── delivery/
│   │   ├── checklist.md         (交付六令, ~200 tokens)
│   │   ├── self-check.md        (自检三令, ~150 tokens)
│   │   └── formats.md           (输出格式模板, ~200 tokens)
│   ├── collaboration/
│   │   └── team.md              (Leader/Teammate/Coach, ~300 tokens)
│   └── meta.md                  (块索引+依赖图+激活规则)
│
├── SKILL.md                     (从 blocks/ 自动生成，保持向后兼容)
└── verify.py                    (验证块化后的全量等于原始 SKILL.md 的行为)
```

**验证标准**：将所有块拼接后与原 SKILL.md 做 diff，行为指令 100% 覆盖。

#### Phase 1：状态追踪器（1 周）

**目标**：实现持久化状态，替代 LLM 的内存。

- 实现 `State` 类的 CRUD
- 通过 Claude Code hooks 连接事件
- 测试：模拟 10 轮对话，验证 failure_count 和 escalation_level 的准确追踪

#### Phase 2：滑动编排器（2 周）

**目标**：实现核心编排算法。

- 实现 `compose_context()` 函数
- 实现 Token 预算管理
- 实现场景检测器
- 测试：对 benchmark 的 9 个场景，验证编排器选择的块集合与人工预期一致

#### Phase 3：平台集成（1 周）

**目标**：在 Claude Code 上实现完整集成。

- Hook 适配器实现
- 端到端测试
- Benchmark 回归验证

#### Phase 4：多平台扩展（2 周）

**目标**：扩展到 Cursor、Copilot CLI 等平台。

- 半动态适配器（Cursor）
- 静态降级适配器（通用）
- 多平台 benchmark 验证

#### 预期收益

| 指标 | 当前 PI | CSE 目标 |
|------|--------|---------|
| 初始加载 tokens | ~15,000-20,000 | ~2,000-3,000 |
| 平均每轮 PI 开销 | ~500-1,000 tokens | ~200-500 tokens |
| 指令遵循率 | 中（指令竞争） | 高（精准注入） |
| 状态持久性 | 无（依赖 LLM 记忆） | 持久化（JSON 文件） |
| 平台适配成本 | 52+ 文件手动同步 | 块仓库 + 适配器自动生成 |

---

## 结论

### PI 的价值

PI 是目前 AI Skill / Prompt Engineering 领域最系统、最完整的工程实践。它证明了：
1. **结构化 prompt 可以显著提升 LLM 的任务执行质量**（benchmark 数据支持）
2. **方法论可以被编码为 LLM 可执行的指令**（元认知增强是可行的）
3. **多平台统一分发是工程上可解决的问题**

### PI 的问题

PI 的核心问题是**静态注入 vs 动态需求**的矛盾：
- 1090 行静态文本试图覆盖所有场景，导致指令膨胀和遵循率下降
- 无持久化状态，关键决策状态（失败次数、战势阶位）完全依赖 LLM 的不可靠记忆
- Eval 驱动的迭代可能导致古德哈特陷阱（为跑分优化而非真实能力提升）

### CSE 方案的核心押注

上下文滑动编辑器（CSE）押注于一个假设：**在正确的时刻注入正确的指令，比一次性注入所有指令更有效**。

这个假设的置信度较高，因为：
1. 信息论支持：减少噪声 → 提升信号 → 更高遵循率
2. 工业实践支持：所有成功的 agent 框架（LangChain/AutoGPT/CrewAI）都采用动态 prompt 组装
3. PI 自身数据支持：渐进式版本（410 行核心 + 按需加载）已是 CSE 理念的雏形

**CSE 不是推翻 PI，而是将 PI 从"操作手册"升级为"导航系统"。**

---

> *报告完成。此文件存放于 `ANALYSIS_REPORT.md`，将推送至 https://github.com/share-skills/pi*
