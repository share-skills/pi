# PI 翻译器：中文 → 英文

> 中文版是源，英文版是翻译产物。
> 属于四阶段流水线的 Phase 4。完整流水线：iterate.md(P1迭代) → COMPILER.md(P2编译) → DISTRIBUTE.md(P3分发) → TRANSLATE.md(P4翻译)

## 翻译范围

| 中文源 | 英文产物 | 说明 |
|--------|---------|------|
| SKILL.md | skills/pi-en/SKILL.md | 精简版英文 |
| SKILL_META.md | *暂不翻译* | 设计文档仅中文 |
| skills/pi/SKILL.md | skills/pi-en/SKILL.md | AgentSkills 标准 |
| claude-code/pi/SKILL.md | claude-code/pi-en/SKILL.md | Claude Code 版 |
| copilot-cli/pi/SKILL.md | copilot-cli/pi-en/SKILL.md | Copilot CLI 版（含 Loop） |
| cursor/rules/pi.mdc | cursor/rules/pi-en.mdc | Cursor 版 |
| kiro/steering/pi.md | kiro/steering/pi-en.md | Kiro 版 |
| openclaw/pi/SKILL.md | openclaw/pi-en/SKILL.md | OpenClaw 版 |
| agents/pi-coach.md | agents/pi-coach-en.md | Coach Agent |
| agents/pi-teammate.md | agents/pi-teammate-en.md | Teammate Agent |
| commands/pi.md | *暂不翻译* | 命令文件 |
| README.zh-CN.md | README.md | 项目 README |

## 翻译原则

### 必须保留（不翻译）

| 类型 | 示例 | 理由 |
|------|------|------|
| emoji | 🏛️⚔️🌊🛡️🌙🔬🦅🐺🦁... | 跨语言通用符号 |
| 格式化输出模板 | `🧠 PI · {scene} · {formation}` | 模板中的占位符翻译，结构不变 |
| 标签代号 | `⚡PI-01` ~ `⚡PI-05` | 全文引用锚点 |
| 技术术语 | build/test/curl/API/CI/CD | 行业通用英文 |
| MMR 格式 | Motivation/Modification/Result | 已是英文 |

### 翻译策略

| 类型 | 策略 | 示例 |
|------|------|------|
| 章节标题 | 意译 | 第一章·道→Ch1 Dao — Wisdom Matrix |
| 古典术语 | 保留拼音+英文释义 | 致人术→Zhiren Arts (Proactive Control) |
| 敕令/戒律 | 祈使句英文 | 搜→读→验→交付→Search→Read→Verify→Deliver |
| 表格内容 | 逐格翻译 | 保持表格结构不变 |
| 行为指令 | 精准翻译 | 保持祈使语气 |
| 灵兽名 | 英文动物名 | 🦅鹰→🦅Eagle, 🐺🐯狼虎→🐺🐯Wolf-Tiger |
| 认知阵 | 意译 | 🧠最强大脑→🧠Supreme Mind |
| frontmatter description | 全文英译 | 保持 ≤1024 字符限制 |

### 文化术语处理

PI 有大量中国哲学/军事术语。翻译策略：

| 层级 | 策略 | 适用场景 |
|------|------|---------|
| **核心概念** | 拼音 + 英文释义首次出现 | 道(Dao)、势(Shi)、截教(Jiejiao) |
| **行为指令** | 纯英文意译 | "穷理尽性"→"Exhaust all possibilities" |
| **装饰性引用** | 仅在 SKILL_META.md 翻译 | 古典引语在精简版已删除 |

## 翻译校验清单

| 序 | 检项 | 动效 |
|---|------|------|
| 一 | **结构一致** | 中英文章节数、表格行数、格式模板数量一致 |
| 二 | **行为等价** | 英文版的祈使句与中文版行为指令一一对应 |
| 三 | **触发条件完整** | 所有触发条件在英文版中存在且语义等价 |
| 四 | **description 合规** | 英文 description ≤1024 字符，双向索引完整 |
| 五 | **frontmatter 合规** | 各平台 frontmatter 符合规范（name: pi-en） |
| 六 | **emoji 保留** | 所有 emoji 在英文版中保留不变 |
| 七 | **格式模板一致** | 输出模板结构一致，占位符翻译但格式不变 |

## 触发条件

- P3 分发完成后触发
- 中文版有结构性改动时必须重新翻译
- 仅文案微调时可选择性更新
