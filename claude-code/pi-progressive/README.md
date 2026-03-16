# PI 渐进式版本 (Progressive Disclosure)

> Copyright (c) 2026 HePin. Licensed under Apache-2.0.

## 什么是渐进式版本？

渐进式版本将完整版 SKILL.md（~1039 行）拆分为**核心版 + 按需加载的参考文件**，减少首次加载的 token 消耗。

## 对比

| 维度 | 完整版 | 渐进式版 |
|------|--------|---------|
| **行数** | ~1039 行 | 核心 ~585 行 + references/ ~511 行 |
| **首次加载** | 全量加载 | 仅加载核心（节省 ~44% token） |
| **详细内容** | 内联 | AI 按需读取 references/ |
| **适用平台** | 所有平台 | 仅支持文件引用的平台（AgentSkills 兼容） |
| **内容完整性** | 100% | 核心 + references/ = 100% |

## 核心版包含什么？

| 内容 | 核心版 | references/ |
|------|--------|------------|
| ⚡ 强制令 + 快速决策表 | ✅ | — |
| 第一章 · 道（场景路由+认知阵） | ✅ | — |
| 第二章 · 法（天则十律） | ✅ | — |
| 第三章 · 术（五略+致人术+九令洞鉴+渐进式交付） | ✅ | — |
| 第四章 · 器（四道合一：编程/测试/产品/运营） | 摘要+链接 | `four-dojos.md` |
| 第五章 · 势 + 第六章 · 灵（战势+灵兽） | 摘要+链接 | `battle-momentum.md` |
| 第七章 · 和（团队协作） | 摘要+链接 | `team-protocol.md` |
| 第八章 · 人（核心协议） | ✅ | — |
| 第八章 · §8.8 共振五式（详细格式） | 摘要+链接 | `resonance-forms.md` |
| 第八章 · §8.9 上下文恢复 | ✅ | — |
| 第九章 · 图（系统架构） | ✅ | — |

## 何时使用渐进式版本？

- **token 预算敏感**：大型项目上下文窗口紧张时
- **首次加载优化**：减少 skill 加载时间和成本
- **平台支持**：Claude Code、Codex CLI、Qoder CLI、OpenClaw 等支持 references/ 的平台

## 何时使用完整版？

- **平台不支持文件引用**：Cursor（.mdc 单文件）、Kiro（steering 单文件）
- **不需要节省 token**：上下文窗口充裕时
- **简单部署**：单文件部署更方便

## 真源关系

```
项目根 SKILL.md（完整版·唯一真源）
    │
    ├── skills/pi/SKILL.md              ← 完整版（AgentSkills 格式）
    ├── skills/pi-progressive/SKILL.md  ← 渐进式核心版 + references/
    ├── claude-code/pi/SKILL.md         ← 完整版（Claude Code 格式）
    ├── claude-code/pi-progressive/     ← 渐进式核心版 + references/
    ├── cursor/rules/pi.mdc            ← 完整版（Cursor 格式）
    ├── kiro/steering/pi.md            ← 完整版（Kiro 格式）
    └── openclaw/pi/SKILL.md           ← 完整版（OpenClaw 格式）
```

> ⚠️ 所有平台文件的内容均从**项目根 SKILL.md** 派生。修改时只改根文件，再同步到各平台。
