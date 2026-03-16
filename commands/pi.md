---
description: PI Wisdom-in-Action Engine v19 — nine chapters (Dao-Fa-Shu-Qi-Shi-Ling-He-Ren-Tu), top-5 mandates with ⚡PI-01~05 KV-Cache anchors, scene router, delivery quality gates, anti-pattern decalogue, six-tier battle momentum, Loop/Auto interaction modes. Invoke to activate structured methodology with positive motivation.
---

Invoke the pi skill and follow it exactly as presented to you.

## Project Context (Auto-Injected)

> The following is auto-injected at invocation to assist 启动三查·查境. Use it to understand the current project state.

**Current branch**: !`git branch --show-current 2>/dev/null || echo '(not a git repo)'`

**Recent commits**:
!`git log --oneline -5 2>/dev/null || echo '(no git history)'`

**Working state**:
!`git diff --stat HEAD 2>/dev/null | tail -5 || echo '(clean or not a git repo)'`

**Project files** (top-level):
!`ls -1 2>/dev/null | head -15 || echo '(empty)'`

## Argument Routing

If the user provided arguments after `/pi`, parse them as follows:

| Argument | Effect |
|----------|--------|
| `loop` | Activate **Loop mode** (§8.2) — every output must end with a question, never auto-exit |
| `auto` | Activate **Auto mode** (§8.2) — default autonomous interaction |
| Scene keyword (编程/ 开发 / fleet /测试/产品/运营/创意/交互/调试/协作/陪伴) | Force-activate that scene (§1.3), skip auto-routing |
| Any other text | Treat as the user's task description, proceed with auto scene routing |

Multiple arguments combine: `/pi loop 编程` = Loop mode + 编程开发 scene.

If no arguments provided, default to Auto mode with auto scene routing.

**After loading PI skill, always output the scene announcement (场景公示) so the user can see which mode and scene are active.**
