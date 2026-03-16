# PI 分发器：SKILL.md → 平台产物

> SKILL.md（精简版）是输入，各平台文件是输出。
> 属于四阶段流水线的 Phase 3。完整流水线：iterate.md(P1迭代) → COMPILER.md(P2编译) → DISTRIBUTE.md(P3分发) → TRANSLATE.md(P4翻译)

## 分发架构

```
SKILL.md (精简版·字节码·含全部规则)
    │
    ├──→ [PURGE] 裁剪 Loop 规则（见 PURGE.md）
    │       │
    │       ├──→ skills/pi/SKILL.md          (AgentSkills 标准)
    │       ├──→ claude-code/pi/SKILL.md     (AgentSkills frontmatter)
    │       ├──→ cursor/rules/pi.mdc         (alwaysApply: true)
    │       ├──→ kiro/steering/pi.md         (inclusion: auto)
    │       └──→ openclaw/pi/SKILL.md        (metadata 单行 JSON, always: true)
    │
    ├──→ [不裁剪] 保留 Loop 规则
    │       └──→ copilot-cli/pi/SKILL.md     (AgentSkills frontmatter)
    │
    └──→ 渐进式版本（按需）
         ├──→ skills/pi-progressive/     (核心版 + references/)
         └──→ claude-code/pi-progressive/ (核心版 + references/)
```

## 平台 frontmatter 映射

| 平台 | frontmatter 差异 | body 差异 |
|------|-----------------|-----------|
| **skills/pi** | AgentSkills 标准（name/description/license/metadata） | PURGE-01: 裁剪 Loop |
| **claude-code/pi** | 同 skills/pi | PURGE-01: 裁剪 Loop |
| **cursor/rules/pi** | `alwaysApply: true`，无 metadata | PURGE-01: 裁剪 Loop |
| **kiro/steering/pi** | `inclusion: auto`，无 metadata | PURGE-01: 裁剪 Loop |
| **openclaw/pi** | metadata 为单行 JSON，`always: true`，emoji 🐲 | PURGE-01: 裁剪 Loop |
| **copilot-cli/pi** | AgentSkills 标准 | 无（保留完整 body） |

## 分发流程

### 1. 全量版分发（6 处）

对每个平台文件：
1. **替换 body**：用 SKILL.md body（frontmatter 以下的内容）替换平台文件的 body
2. **执行 PURGE**：对适用平台按 PURGE.md 规则裁剪（Copilot CLI 跳过此步）
3. **保留 frontmatter**：各平台 frontmatter 格式不同，保持原样
4. **校验 description**：确认所有平台 description 一致（字符级一致）

### 2. 渐进式版本分发（按需）

仅在支持 references/ 的平台（AgentSkills 兼容平台）实施：

1. **拆分**：SKILL.md → 核心版（高频章节）+ references/（四道场/战势/共振五式/团队协议）
2. **校验**：
   - 核心版 + references/ 内容总和 ≥ SKILL.md body 的 95%
   - 核心版中每个 `[references/X.md]` 链接指向存在的文件
   - `skills/pi-progressive/` 与 `claude-code/pi-progressive/` 内容一致

### 3. 分发校验清单

| 序 | 检项 | 动效 |
|---|------|------|
| 一 | **body 一致（purged）** | 裁剪后的 5 个平台文件 body 一致 |
| 二 | **body 完整（unpurged）** | Copilot CLI body 与 SKILL.md body 一致 |
| 三 | **description 一致** | 所有平台 description 字符级一致 |
| 四 | **frontmatter 合规** | 各平台 frontmatter 符合对应规范 |
| 五 | **PURGE 无悬空** | 裁剪后无悬空引用（引用 Loop 但 Loop 已删） |
| 六 | **渐进式覆盖** | 核心版 + references/ ≥ 95% 覆盖 |
| 七 | **引用链完整** | references/ 文件均存在且可访问 |
| 八 | **跨目录同步** | progressive 的 skills/ 与 claude-code/ 一致 |

## 不支持 references/ 的平台

Cursor (.mdc) 和 Kiro (steering .md) 不支持 references/，始终使用完整单文件版。

## 触发条件

- SKILL.md 有任何改动后触发
- 仅 description 变更时，只同步 frontmatter
- 仅 body 变更时，只同步 body
- PURGE.md 规则变更时，需重新分发所有适用平台
