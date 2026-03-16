# PI 发布流程

> 一条命令触发：`使用 PUBLISH.md 进行发布流程`
> 从 SKILL_META.md 到全平台就绪，AI 直接执行，中途含校验门禁。

## 前置条件

- SKILL_META.md 已完成本轮迭代（P0/P1 = 0）
- CHANGE_LOG.md 已记录本轮改动
- 当前分支干净（无未暂存的非 PI 文件）

## 执行流程

---

### Phase 0: 版本决策

**目标**：确定发布版本号，统一全链路。

**执行**：

```
步骤 0.1  读取 SKILL_META.md frontmatter 中的 version 字段
步骤 0.2  读取 CHANGE_LOG.md，统计自上次发布以来的改动：
          - 有新增能力/重大结构变更 → 主版本号+1（如 19.0.0 → 20.0.0）
          - 有行为改动但无新增能力 → 次版本号+1（如 19.0.0 → 19.1.0）
          - 仅修复/优化/文案 → 修订号+1（如 19.0.0 → 19.0.1）
步骤 0.3  向用户确认版本号：
          "本次发布版本建议为 v{X.Y.Z}，原因：{依据}。确认？"
步骤 0.4  用户确认后，更新 SKILL_META.md frontmatter version 字段
          （SKILL.md 的 version 将在 P2 编译时自动同步）
```

---

### Phase 1: 预检

**目标**：确认迭代已收敛，发布前状态健康。

**执行**：

```
步骤 1.1  读取 SKILL_META.md 全文，确认文件完整可读
步骤 1.2  读取 CHANGE_LOG.md 最新条目，确认本轮改动已记录
步骤 1.3  读取 COMPILER.md 全文，加载编译规则
步骤 1.4  读取 DISTRIBUTE.md 全文，加载分发规则
步骤 1.5  读取 PURGE.md 全文，加载裁剪规则
步骤 1.6  读取 TRANSLATE.md 全文，加载翻译规则
步骤 1.7  读取 README.zh-CN.md，加载项目说明（后续同步用）
步骤 1.8  运行 git status，确认工作区状态
```

**校验门禁 1**：
- [ ] SKILL_META.md 可读且非空
- [ ] CHANGE_LOG.md 最新条目日期 = 今天
- [ ] COMPILER.md / DISTRIBUTE.md / PURGE.md / TRANSLATE.md 均可读

> ❌ 任一失败 → 停止，报告缺失文件，等待用户修复。

---

### Phase 2: 编译（P2）

**目标**：从 SKILL_META.md 编译生成 SKILL.md（原版）+ SKILL_LITE.md（白话版）。

**执行**：

```
步骤 2.1  【原版编译】按 COMPILER.md 全局剥离规则，从 SKILL_META.md 生成精简版内容：
          - 删除：章节开头古典引语、经典列、思想源列、示例块、本质段、
                  为什么段、用户干预点/联动说明段、尾部哲理签名
          - 保留：行为指令、认知策略（MBTI/认知阵/认知栈/认知流管线）、
                  格式模板、触发条件、emoji
          - 整章删除：Ch2 天则十律、Ch9 系统总览
          - 章节标题：`第X章 · Y — Z` → `X. Z`
          - Ch1.1 十六源：压缩为 1 行
          - Ch1.2 六维认知原型：保留完整表 + AI 行为映射表
          - Ch8.8 共振五式：最大压缩区（删本质段/示例/为什么段，保留格式+触发）

步骤 2.2  将编译结果写入 SKILL.md（保留原 frontmatter 不变）

步骤 2.3  【白话版编译】按 COMPILER_LITE.md 规则，以 SKILL.md 为基础生成白话版内容：
          - 术语翻译：9 大映射表，100+ 古典/军事/哲学/MBTI 术语 → 白话文
          - MBTI→白话行为描述（不删除，翻译为收敛/发散/工程/自洽/共情等）
          - 十二灵兽→白话精神+困境信号（不删除，翻译为直白描述）
          - 共振五式→全部保留，术语替换（明链→思路展示 等）
          - 结构精简：9 章 → 7 个扁平章节（删 Ch2+Ch9，同 COMPILER.md）
          - Coach 巡检协议→保留，术语替换
          - §X.Y 交叉引用→内联到上下文
          - PURGE-01 照做（Loop 按平台裁剪）

步骤 2.4  将白话版写入 SKILL_LITE.md
```

**校验门禁 2**（逐项检查，全部通过才继续）：

```
步骤 2.5  【原版校验】行为指令完整性检查：
          - 逐条比对 SKILL_META.md 中的祈使句，确认 SKILL.md 中存在
          - 重点检查：五敕令、反模式十戒、快速决策表、编程四令、
            调试六步、九令洞鉴、交付六令、自检三令

步骤 2.6  格式模板完整性检查：
          - 场景公示格式 `🧠 PI · {场景名} · ...`
          - 触发通知格式 `🔔 PI · {阶位} · ...`
          - 明链三档格式（⚡/🧠/🐲）
          - 明证格式 `🎯 结论: ...`
          - 明树格式 `🌳 问题树 ...`
          - 明心格式 `🧠 PI状态: ...`
          - 明约格式 `📋 交付确认 ...`
          - 已试策略簿格式 `📝 已试: ...`
          - 快照格式 `🔄 快照: ...`
          - 善始善终五项输出
          - 恢复协议格式 `🔄 PI · 恢复 · ...`
          - 三省格式 `📜 三省: ...`
          - MMR commit 格式
          - PI·战报格式

步骤 2.7  触发条件完整性检查：
          - 每个格式模板的触发条件在 SKILL.md 中有定义
          - 战势各阶触发（失败次数→阶位）清晰
          - 难度三档判定条件完整

步骤 2.8  统计 SKILL.md 行数，与上一版本对比

步骤 2.9  【白话版校验】按 COMPILER_LITE.md 编译校验清单（8项）：
          - 行为完全覆盖：LITE 版覆盖 SKILL.md 的全部行为指令（一条不少）
          - 术语零残留：不出现白话映射表左列的术语原文
          - § 引用零残留：不出现 §X.Y 格式的交叉引用
          - 独立可读：不需要阅读任何其他文件即可理解全部内容
          - MBTI 零残留：不出现 MBTI/Ni/Te/Fi/Se 等术语（但保留白话行为描述）
          - 功能等价：原版每个格式模板、触发条件均有白话等价物
          - emoji 保留：保留 emoji 用于视觉分区（含灵兽 emoji）
          - PURGE 兼容：LITE 版包含 Loop 规则，可被 PURGE-01 正常裁剪

步骤 2.10 统计 SKILL_LITE.md 行数
```

> ❌ 任一检查失败 → 定位丢失内容，从 SKILL_META.md 补回，重新执行 2.3-2.5。
>
> ✅ 全部通过 → 输出：`✅ P2 编译完成。SKILL.md {行数}行 + SKILL_LITE.md {行数}行。行为指令/格式模板/触发条件完整。白话版校验通过。`

---

### Phase 3: 分发（P3）

**目标**：SKILL.md + SKILL_LITE.md → 6 平台文件（双版本）+ 渐进式版本。

**执行**：

```
步骤 3.1  提取 SKILL.md 的 body（frontmatter 以下内容）
步骤 3.1b 提取 SKILL_LITE.md 的 body

步骤 3.2  执行 PURGE-01 裁剪（生成 purged body）：
          - 删除 Loop 模式规则（交互模式表 Loop 行、Loop 规则7条、
            退出陷阱表、启动协议、Loop 警告注解）
          - 调整：模式加载矩阵 Loop 列引用、渐进式交付 Loop 引用、
            循环交互 Loop 标注
          - 校验裁剪后无悬空 Loop 引用

步骤 3.2b 对 SKILL_LITE.md body 执行同样的 PURGE-01 裁剪（生成 purged LITE body）

步骤 3.3  分发 purged body 到 5 个平台（保留各自 frontmatter）：
          3.3.1  读取 skills/pi/SKILL.md → 替换 body → 写回
          3.3.2  读取 claude-code/pi/SKILL.md → 替换 body → 写回
          3.3.3  读取 cursor/rules/pi.mdc → 替换 body → 写回
          3.3.4  读取 kiro/steering/pi.md → 替换 body → 写回
          3.3.5  读取 openclaw/pi/SKILL.md → 替换 body → 写回

步骤 3.4  分发完整 body 到 Copilot CLI（不裁剪）：
          3.4.1  确认 copilot-cli/pi/ 目录存在（不存在则创建）
          3.4.2  读取或创建 copilot-cli/pi/SKILL.md → 写入完整 body

步骤 3.5  分发白话版到各平台（SKILL_LITE.md body，无需 PURGE）：
          3.5.1  写入 skills/pi/SKILL_LITE.md
          3.5.2  写入 claude-code/pi/SKILL_LITE.md
          3.5.3  写入 cursor/rules/pi-lite.mdc（使用 cursor LITE frontmatter）
          3.5.4  写入 kiro/steering/pi-lite.md（使用 kiro LITE frontmatter）
          3.5.5  写入 openclaw/pi/SKILL_LITE.md
          3.5.6  写入 copilot-cli/pi/SKILL_LITE.md

步骤 3.6  同步 description：
          - 提取 SKILL_META.md 的 description
          - 确认所有原版平台文件的 description 与之一致
          - LITE 版使用白话版 description（从 COMPILER_LITE.md 规则生成）
          - 如不一致，更新为最新版
```

**校验门禁 3**：

```
步骤 3.7  Body 一致性校验：
          - 5 个 purged 平台文件 body 互相一致
          - copilot-cli body 与 SKILL.md body 一致
          - 6 个 LITE 平台文件 body 互相一致

步骤 3.8  Description 一致性校验：
          - 所有原版平台文件 description 字符级一致
          - 所有 LITE 平台文件 description 字符级一致

步骤 3.9  Frontmatter 合规校验：
          - skills/pi: name/description/license/metadata 格式正确
          - claude-code/pi: 同上
          - cursor/rules/pi: alwaysApply: true 存在
          - kiro/steering/pi: inclusion: auto 存在
          - openclaw/pi: metadata 单行 JSON, always: true 存在
          - copilot-cli/pi: AgentSkills 标准格式
          - LITE 版各平台 frontmatter 同样合规（name: pi-lite）

步骤 3.10 PURGE 无悬空校验：
          - 在 purged 文件中搜索 "Loop" 关键词
          - 确认无残留的 Loop 引用（允许 Auto 模式中的合理提及）

步骤 3.11 Description 内容校验：
          - description 中提到的概念在 SKILL.md 中均有定义
          - 已删除的章节（Ch2/Ch9）不应在 description 中被引用
          - 中文/英文 description 均 ≤ 1024 字符
          - LITE 版 description 中提到的概念在 SKILL_LITE.md 中均有定义
```

> ❌ 任一失败 → 修复后重新执行对应步骤。
>
> ✅ 全部通过 → 输出：`✅ P3 分发完成。6 平台×2 版本（原版+白话版）已同步。PURGE-01 已执行。Description 一致。`

---

### Phase 4: 翻译（P4）

**目标**：中文产物 → 英文产物。

**执行**：

```
步骤 4.1  翻译 SKILL.md body → 英文版 body
          翻译规则：
          - 保留不翻译：emoji、⚡PI-01~05 标签、技术术语、MMR 格式
          - 意译：章节标题、行为指令（祈使句）、表格内容、description
          - 拼音+释义：核心概念首次出现（道 Dao、势 Shi、截教 Jiejiao）
          - 灵兽名翻译：鹰 Eagle、狼 Wolf、狮 Lion 等

步骤 4.1b 翻译 SKILL_LITE.md body → 英文版 LITE body
          翻译规则：
          - 同上，但 LITE 本身已无古典术语，翻译更直接
          - 保留不翻译：emoji、标签代号、技术术语

步骤 4.2  分发英文版到各平台：
          4.2.1  skills/pi-en/SKILL.md（purged body 英文版）
          4.2.2  claude-code/pi-en/SKILL.md（purged body 英文版）-- 如果目录存在
          4.2.3  copilot-cli/pi-en/SKILL.md（完整 body 英文版）-- 如果目录存在
          4.2.4  cursor/rules/pi-en.mdc（purged body 英文版）
          4.2.5  kiro/steering/pi-en.md（purged body 英文版）
          4.2.6  openclaw/pi-en/SKILL.md（purged body 英文版）-- 如果目录存在

步骤 4.2b 分发英文 LITE 版到各平台：
          4.2b.1 skills/pi-en/SKILL_LITE.md
          4.2b.2 claude-code/pi-en/SKILL_LITE.md -- 如果目录存在
          4.2b.3 copilot-cli/pi-en/SKILL_LITE.md -- 如果目录存在
          4.2b.4 cursor/rules/pi-en-lite.mdc
          4.2b.5 kiro/steering/pi-en-lite.md
          4.2b.6 openclaw/pi-en/SKILL_LITE.md -- 如果目录存在

步骤 4.3  翻译 agents：
          4.3.1  agents/pi-coach.md → agents/pi-coach-en.md
          4.3.2  agents/pi-teammate.md → agents/pi-teammate-en.md

步骤 4.4  翻译 README：
          4.4.1  README.zh-CN.md → README.md（英文版）
```

**校验门禁 4**：

```
步骤 4.5  结构一致性：
          - 中英文章节数一致
          - 中英文表格行数一致
          - 中英文格式模板数量一致

步骤 4.6  行为等价性：
          - 英文版祈使句与中文版行为指令一一对应
          - 所有触发条件在英文版中存在且语义等价

步骤 4.7  Frontmatter 合规：
          - 英文版 name: pi-en
          - 英文版 description ≤ 1024 字符（中文版同理）

步骤 4.8  Emoji 保留：
          - 所有 emoji 在英文版中保留不变
```

> ❌ 任一失败 → 修复后重新执行对应步骤。
>
> ✅ 全部通过 → 输出：`✅ P4 翻译完成。英文版已同步。行为等价校验通过。`

---

### Phase 5: 渐进式版本（按需）

**目标**：为支持 references/ 的平台生成渐进式版本。

**执行**：

```
步骤 5.1  从 SKILL.md 拆分：
          - 核心版：高频章节（强制令+决策表+Ch1+Ch3+Ch8 核心）
          - references/four-dojos.md：Ch4 四道场
          - references/battle-momentum.md：Ch5 战势 + Ch6 灵兽
          - references/resonance-forms.md：Ch8.8 共振五式详细
          - references/team-protocol.md：Ch7 团队协作

步骤 5.2  写入 skills/pi-progressive/
步骤 5.3  写入 claude-code/pi-progressive/（内容与 5.2 一致）
```

**校验门禁 5**：

```
步骤 5.4  核心版 + references/ 内容 ≥ SKILL.md body 的 95%
步骤 5.5  核心版中每个 references/ 链接指向存在的文件
步骤 5.6  skills/pi-progressive/ 与 claude-code/pi-progressive/ 内容一致
```

> 此阶段为可选。跳过时输出：`⏭️ 渐进式版本跳过（按需执行）。`

---

### Phase 6: 最终确认

**执行**：

```
步骤 6.1  运行 git status，列出所有变更文件

步骤 6.2  输出发布摘要：

          ┌─────────────────────────────────────┐
          │         📦 PI 发布摘要               │
          ├─────────────────────────────────────┤
          │ 版本:     {version}                  │
          │ SKILL_META: {行数} 行（迭代真源）      │
          │ SKILL.md:   {行数} 行（原版精简）      │
          │ SKILL_LITE: {行数} 行（白话版）        │
          │ 中文平台:   {N} 个文件×2版本已同步      │
          │ 英文平台:   {N} 个文件×2版本已同步      │
          │ PURGE:     {规则} 已执行               │
          │ 渐进式:    {已执行/跳过}               │
          ├─────────────────────────────────────┤
          │ ✅ P2 编译通过                        │
          │ ✅ P3 分发通过                        │
          │ ✅ P4 翻译通过                        │
          │ {✅/⏭️} P5 渐进式 {通过/跳过}          │
          ├─────────────────────────────────────┤
          │ 📝 变更文件清单:                      │
          │   {git status 变更文件列表}            │
          └─────────────────────────────────────┘

步骤 6.3  等待用户确认：
          "以上是本次发布的所有变更。确认后我将暂存所有文件，
           你可以 review 后推送到 GitHub。
           确认发布？"
```

**用户确认后**：

```
步骤 6.4  暂存所有变更文件（git add 具体文件列表，不用 -A）
步骤 6.5  创建 commit：
          chore: publish PI v{version}

          Motivation:
          完成 P1→P2→P3→P4 全流水线发布

          Modification:
          - SKILL_META.md: {本轮核心改动}
          - SKILL.md: 从 SKILL_META.md 编译（{行数}行）
          - 6 平台中文版同步 + PURGE-01 执行
          - 英文版翻译同步
          - {其他改动}

          Result:
          全平台文件就绪，待推送至 GitHub

步骤 6.6  输出：
          "✅ 发布完成。commit 已创建。
           推送命令: git push origin main"
```

> ⚠️ 不自动 push。推送由用户手动执行。

---

## 异常处理

| 异常 | 处理 |
|------|------|
| 编译后行为指令丢失 | 从 SKILL_META.md 补回，重新编译 |
| PURGE 后悬空引用 | 检查裁剪规则，修复引用 |
| Description 超 1024 字符 | 压缩 description，保留核心索引（中文/英文均需 ≤ 1024 字符） |
| 平台文件不存在 | 创建目录和文件，使用对应 frontmatter 模板 |
| 翻译后结构不一致 | 逐章比对，补齐缺失部分 |
| 用户中途要求停止 | 输出当前进度，标注已完成/未完成阶段 |

## 快速参考

```
触发:    "使用 PUBLISH.md 进行发布流程"
跳过翻译: "使用 PUBLISH.md 发布，跳过翻译"
仅编译:  "使用 PUBLISH.md 仅执行 P2 编译"
仅分发:  "使用 PUBLISH.md 仅执行 P3 分发"
```
